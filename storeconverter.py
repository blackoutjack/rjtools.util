# Dump the contents of a data source to a target data store.
#
import pandas
from sqlalchemy import (
    create_engine, MetaData, Table, Column, String, Text, Date, DateTime,
    TIMESTAMP, Integer, select, insert, text)
from sqlalchemy.exc import OperationalError

from util.msg import info, warn, dbg, err
from util.convert import parse_date_idem, parse_timestamp, parse_iso_date, parse_user_date
from util.type import has_type, type_error, empty
from util.schema import DataType

COPY_DB_SCHEMA = False
FIX_DATES = False  # True here requires COPY_DB_SCHEMA to be False

COLUMN_CONVERTERS = {
    DataType.AUTOID: int,
    DataType.STRING: str,
    DataType.TEXT: str,
    DataType.DATE: parse_date_idem,
    DataType.DATETIME: parse_timestamp,
    DataType.TIMESTAMP: parse_timestamp,
    DataType.AUTOTIMESTAMP: parse_timestamp,
    DataType.CREATETIMESTAMP: parse_timestamp,
    # %%% What here for FORMULA?
    DataType.FORMULA: lambda v: None,
}

def getTypeConverters(tableSchema):
    return { col: COLUMN_CONVERTERS[tableSchema.columnTypes[col]] for col in tableSchema.columns }

class ConverterOptions:
    def __init__(self, tableSchemas, recordFilter=None):
        self.SCHEMAS = tableSchemas
        self.RECORD_FILTER = recordFilter

class Converter:

    def __init__(self, source, target, dbOptions):
        # %%% Do type checking
        self.opts = dbOptions
        self.source = source
        self.sourceDef = source.api.storeDef
        self.target = target
        self.targetDef = target.api.storeDef

        self.sourceTables = source.api.list_tables()

        self.converters = { t.name: getTypeConverters(t) for t in self.opts.SCHEMAS.values() }

        #self.saveCopy(target)
        info("Clearing target store %s" % self.targetDef.ID)
        target.clear()

        if self.sourceDef.KIND == "db":
            self.metadata = MetaData()
            self.sourceEngine = create_engine(self.sourceDef.URL)

        if self.targetDef.KIND == "db":
            self.metadata = MetaData()
            self.targetEngine = create_engine(self.targetDef.URL)

    def generate_table(self, schema):
        tableName = schema.name
        dbg("TABLE %s" % tableName)
        tableKey = schema.key
        indexes = schema.indexes
        columns = []
        if tableKey is None:
            columns.append(Column(
                "Id",
                Integer(),
                nullable=False,
                index=True,
                primary_key=True,
                autoincrement=True))

        columnTypes = schema.columnTypes

        for colName in schema.columns:
            if has_type(tableKey, str):
                isPrimary = colName == tableKey
            elif has_type(tableKey, tuple):
                isPrimary = colName in tableKey
            elif has_type(tableKey, None):
                isPrimary = False
            else:
                type_error("tableKey", type(tableKey), "str|tuple")

            isIndex = colName in indexes
            dataType = columnTypes[colName]

            isNullable = True
            autoIncrement = False
            serverDefault = None

            # %%% Make this based on declarative config
            if dataType == DataType.AUTOID:
                isNullable = False
                autoIncrement = True
                colType = Integer
            elif dataType == DataType.FORMULA:
                # Formula columns are only maintained in spreadsheets
                continue
            elif dataType == DataType.STRING:
                size = 32 if isPrimary else 256
                colType = String(size)
            elif dataType == DataType.TEXT:
                colType = Text()
            elif dataType == DataType.DATE:
                colType = Date()
            elif dataType == DataType.DATETIME:
                colType = DateTime()
            elif dataType == DataType.TIMESTAMP:
                colType = TIMESTAMP()
            elif dataType == DataType.AUTOTIMESTAMP:
                colType = TIMESTAMP()
                isNullable = False
                serverDefault=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
            elif dataType == DataType.CREATETIMESTAMP:
                serverDefault=text("CURRENT_TIMESTAMP")
                colType = TIMESTAMP()
                isNullable = False
            else:
                raise ValueError("Unexpected column type for table %s: %r" % (tableName, dataType))

            columns.append(Column(
                colName,
                colType,
                nullable=isNullable,
                index=isIndex,
                primary_key=isPrimary,
                autoincrement=autoIncrement,
                server_default=serverDefault
            ))

        # New table is injected into metadata.
        Table(tableName, self.metadata, *columns)

    def create_last_id_table(self):
        columns = [
            Column(
                "table_name",
                String(32),
                nullable=False,
                index=True,
                primary_key=True,
            ),
            Column(
                "last_int_id",
                String(32),
                nullable=False,
                index=False,
                primary_key=False,
            ),
        ]
        # New table is injected into metadata.
        Table("LastId", self.metadata, *columns)

    def load_last_id(self, nextIdTable, table):
        if len(table.primary_key.columns) == 0:
            info("No primary key for table %s" % table.name)
            return
        if len(table.primary_key.columns) > 1:
            info("Last id not supported for multiple primary keys in table %s" % table.name)
            return
        primaryKey = table.primary_key.columns[0]
        if primaryKey.autoincrement is True:
            info("Skipping last id tracking for autoincrement primary key in table %s" % table.name)
            return
        selectStmt = select(primaryKey)
        with self.targetEngine.connect() as conn:
            result = conn.execute(selectStmt)
            rows = result.all()
        lastIntId = 0
        for row in rows:
            rowId = row[0]
            if not rowId.isdecimal():
                continue
            intId = int(rowId)
            if intId > lastIntId:
                lastIntId = intId
        insertStmt = insert(nextIdTable).values({
            "table_name": table.name,
            "last_int_id": lastIntId
        })
        with self.targetEngine.connect() as conn:
            conn.execute(insertStmt)
            conn.commit()

    def convert(self):
        info("Converting: %s => %s" % (self.sourceDef.ID, self.targetDef.ID))
        if self.targetDef.KIND == "db":
            self.create_last_id_table()
            for table in self.opts.SCHEMAS.values():
                if self.sourceDef.KIND == "db" and COPY_DB_SCHEMA:
                    # Simply copy the schema from the existing database.
                    Table(table.name, self.metadata, autoload_with=self.sourceEngine)
                else:
                    # Generate table definitions from the shrem data types.
                    self.generate_table(table)

            try:
                self.metadata.create_all(self.targetEngine)
            except OperationalError as ex:
                err("Failed to create database tables in %s: %s" % (self.targetDef.ID, str(ex)))
                return
        elif self.targetDef.KIND == "excel":
            self.excelWriter = pandas.ExcelWriter(
                self.targetDef.URL,
                engine="xlsxwriter",
                mode="w",
                datetime_format="m/d/yyyy",
                date_format="m/d/yyyy")
        else:
            err("Unsupported target kind for conversion: %s" % self.targetDef.KIND)
            return

        expectedTables = self.opts.SCHEMAS.keys()

        if self.sourceDef.KIND == "googlesheets":
            gidNames = self.sourceTables.items()
            for gid, title in gidNames:
                if title not in expectedTables:
                    warn("Skipping sheet %s" % title)
                    continue
                url = "%s/export?format=csv&gid=%d" % (self.sourceDef.URL, gid)
                dbg("CSV URL FOR GOOGLE SHEET %s: %s" % (title, url))
                info("Converting table %s (gid=%d)" % (title, gid))

                tableConverters = self.converters[title] if title in self.converters else None

                df = pandas.read_csv(url, converters=tableConverters);

                self.dumpToTarget(title, df)

        elif self.sourceDef.KIND == "excel":
            for title in self.sourceTables:
                if title not in expectedTables:
                    warn("Skipping sheet %s" % title)
                    continue
                info("Converting table %s" % title)

                tableConverters = self.converters[title] if title in self.converters else None

                df = pandas.read_excel(
                    self.sourceDef.URL,
                    sheet_name=title,
                    converters=tableConverters);
                self.dumpToTarget(title, df)

        elif self.sourceDef.KIND == "db":
            for title in self.sourceTables:
                if title not in expectedTables:
                    warn("Skipping table %s" % title)
                    continue
                info("Converting table %s" % title)

                schema = self.opts.SCHEMAS[title]

                colTypes = schema.columnTypes

                df = pandas.read_sql(title, self.sourceDef.URL)

                if FIX_DATES:
                    def fixDate(date):
                        if empty(date): return None
                        try:
                            return parse_iso_date(date)
                        except ValueError:
                            try:
                                return parse_user_date(date)
                            except ValueError:
                                err("Failed to parse date value in column %s: %r" % (col, date))
                                return None

                    for col in schema.columns:
                        if colTypes[col] == DataType.DATE:
                            if df[col].dtype.kind != 'M':
                                df[col] = df[col].apply(fixDate)

                self.dumpToTarget(title, df)
        else:
            err("Unsupported source kind for conversion: %s" % self.sourceDef.KIND)
            return

        if self.targetDef.KIND == "excel":
            self.excelWriter.close()

    def applyFilters(self, tableName, df):
        if tableName not in self.opts.RECORD_FILTER:
            return

        schema = self.opts.SCHEMAS[tableName]
        columnTypes = schema.columnTypes

        hasPrimaryKeys = False
        if hasattr(self, "metadata"):
            table = self.metadata.tables[tableName]
            primaryCols = table.primary_key.columns
            # %%% Hack to avoid using auto-generated ids from db records
            # %%% (which won't be there in spreadsheets)
            dbg("PRIMARYCOLS: %d %r" % (len(primaryCols), primaryCols[0]))
            hasPrimaryKeys = len(primaryCols) > 0 and primaryCols[0].autoincrement is not True
        dbg("TABLE: %s HASPRIMARYKEYS: %r" % (tableName, hasPrimaryKeys))

        for record in self.opts.RECORD_FILTER[tableName]:
            if not hasPrimaryKeys:
                # Just match on all given columns.
                cond = None
                for colName in record:
                    recordValue = record[colName]
                    # Record may have empty where the dataframe has NULL.
                    # %%% Assumes that columns which can be empty cannot factor
                    # %%% into the identity of a row.
                    if recordValue == "": continue

                    if columnTypes[colName] is DataType.FORMULA: continue

                    dbg("COLNAME: %s, VALUE: %s" % (colName, record[colName]))
                    if cond is None:
                        cond = df[colName] == record[colName]
                    else:
                        cond = cond & (df[colName] == record[colName])
                if cond is not None:
                    dbg("0 DROPPING FROM %s SIZE: %d" % (tableName, len(df[colName])))
                    dbg("COND:\n%r" % cond)
                    df.drop(df[cond].index, inplace=True)
                    dbg("0 SIZE: %d" % len(df[colName]))
            else:
                cond = None
                for primaryCol in primaryCols:
                    primaryName = primaryCol.name
                    if cond is None:
                        cond = (df[primaryName] == record[primaryName])
                    else:
                        cond = cond & (df[primaryName] == record[primaryName])
                if cond is not None:
                    dbg("1 DROPPING FROM %s SIZE: %d" % (tableName, len(df[primaryName])))
                    dbg("COND:\n%r" % cond)
                    df.drop(df[cond].index, inplace=True)
                    dbg("1 SIZE: %d" % len(df[primaryName]))

    def dumpToTarget(self, tableName, df):
        tableConfig = self.opts.SCHEMAS[tableName]
        columnConfig = tableConfig.columnTypes

        # Apply any specified data filters.
        self.applyFilters(tableName, df)

        if self.targetDef.KIND == "db":
            columnsToOmit = [c for c in tableConfig.columns if columnConfig[c] == DataType.FORMULA]
            if len(columnsToOmit) > 0:
                df.drop(columns=columnsToOmit, inplace=True, errors='ignore')

            df.to_sql(tableName, con=self.targetEngine, if_exists='append', index=False)
            self.load_last_id(self.metadata.tables["LastId"], self.metadata.tables[tableName])
        elif self.targetDef.KIND == "excel":
            # %%% Fill in FORMULA columns

            df.to_excel(self.excelWriter, sheet_name=tableName, header=True, index=False)
        else:
            err("Unsupported target kind for conversion: %s" % self.targetDef.KIND)


