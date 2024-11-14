# Dump the contents of a data source to a target data store.
#
import os

import pandas
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, Date, Integer, select, insert

from util.msg import info, warn, dbg, err
from util.convert import parse_date
from util.type import has_type, type_error, empty, nonempty

class ConverterOptions:
    def __init__(self, sheetsToConvert, omitDbColumns={}, dateColumns=[], commentColumns=[], convertDates=False, recordFilter=None):
        # %%% Should check all these for type/structure
        self.SHEETS_TO_CONVERT = sheetsToConvert
        self.OMIT_COLUMNS_FOR_DB = omitDbColumns
        self.DATE_COLUMNS = dateColumns
        self.COMMENT_COLUMNS = commentColumns
        self.CONVERT_DATES = convertDates
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

        #self.saveCopy(target)
        info("Clearing target store %s" % self.targetDef.ID)
        target.clear()

        if self.targetDef.KIND == "db":
            self.metadata = MetaData()
            self.engine = create_engine(self.targetDef.URL)

    def generate_table(self, sheetSchema):
        sheetName = sheetSchema.name
        dbg("TABLE %s" % sheetName)
        tableKey = sheetSchema.key
        indexes = sheetSchema.indexes
        columns = []
        if tableKey is None:
            columns.append(Column(
                "Id",
                Integer(),
                nullable=False,
                index=True,
                primary_key=True,
                autoincrement=True))

        for colName in sheetSchema.columns:
            if has_type(tableKey, str):
                isPrimary = colName == tableKey
            elif has_type(tableKey, tuple):
                isPrimary = colName in tableKey
            elif has_type(tableKey, None):
                isPrimary = False
            else:
                type_error("tableKey", type(tableKey), "str|tuple")

            isIndex = colName in indexes
            isNullable = True
            if sheetName in self.opts.OMIT_COLUMNS_FOR_DB:
                toOmit = self.opts.OMIT_COLUMNS_FOR_DB[sheetName]
                if colName in toOmit:
                    continue
            if colName in self.opts.COMMENT_COLUMNS:
                colType = Text()
            elif colName in self.opts.DATE_COLUMNS:
                colType = Date()
            else:
                size = 32 if isPrimary else 256
                colType = String(size)

            columns.append(Column(
                colName,
                colType,
                nullable=isNullable,
                index=isIndex,
                primary_key=isPrimary))

        table = Table(
            sheetName,
            self.metadata,
            *columns)

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
        table = Table(
            "LastId",
            self.metadata,
            *columns,
        )

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
        with self.engine.connect() as conn:
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
        with self.engine.connect() as conn:
            conn.execute(insertStmt)
            conn.commit()

    def convert(self):
        info("Converting: %s => %s" % (self.sourceDef.ID, self.targetDef.ID))
        if self.targetDef.KIND == "db":
            self.create_last_id_table()
            for sheet in self.opts.SHEETS_TO_CONVERT:
                sheetSchema = sheet.schema
                self.generate_table(sheetSchema)

            try:
                self.metadata.create_all(self.engine)
            except OperationalError as ex:
                err("Failed to create database tables in %s: %s" % (self.targetDef.ID, str(ex)))
                return
        elif self.targetDef.KIND == "excel":
            self.excelWriter = pandas.ExcelWriter(
                self.targetDef.URL,
                mode="w",
                date_format="m/d/Y",
                datetime_format="m/d/Y HH:MM:SS")
        else:
            err("Unsupported target kind for conversion: %s" % self.targetDef.KIND)
            return

        expectedTables = [table.NAME for table in self.opts.SHEETS_TO_CONVERT]
        if self.sourceDef.KIND == "googlesheets":
            gidNames = self.sourceTables.items()
            for gid, title in gidNames:
                if title not in expectedTables:
                    warn("Skipping sheet %s" % title)
                    continue
                url = "%s/export?format=csv&gid=%d" % (self.sourceDef.URL, gid)
                dbg("CSV URL FOR GOOGLE SHEET %s: %s" % (title, url))
                info("Converting table %s (gid=%d)" % (title, gid))
                dateConverters = None

                if self.opts.CONVERT_DATES:
                    dateConverters = {colName: parse_date for colName in self.opts.DATE_COLUMNS}

                df = pandas.read_csv(url, converters=dateConverters);

                self.dumpToTarget(title, df)

        elif self.sourceDef.KIND == "excel":
            for title in self.sourceTables:
                if title not in expectedTables:
                    warn("Skipping sheet %s" % title)
                    continue
                info("Converting table %s" % title)

                dateConverters = None
                if self.opts.CONVERT_DATES:
                    dateConverters = {colName: parse_date for colName in self.opts.DATE_COLUMNS}

                df = pandas.read_excel(self.sourceDef.URL, sheet_name=title, converters=dateConverters);
                self.dumpToTarget(title, df)

        elif self.sourceDef.KIND == "db":
            for title in self.sourceTables:
                if title not in expectedTables:
                    warn("Skipping table %s" % title)
                    continue
                info("Converting table %s" % title)

                dateFormats = None
                if self.opts.CONVERT_DATES:
                    dateFormats = {colName: '%m/%d/%Y' for colName in self.opts.DATE_COLUMNS}

                df = pandas.read_sql(title, self.sourceDef.URL, parse_dates=dateFormats);
                self.dumpToTarget(title, df)
        else:
            err("Unsupported source kind for conversion: %s" % self.sourceDef.KIND)
            return

        if self.targetDef.KIND == "excel":
            self.excelWriter.close()

    def applyFilters(self, tableName, df):
        if tableName not in self.opts.RECORD_FILTER:
            return

        for record in self.opts.RECORD_FILTER[tableName]:
            table = self.metadata.tables[tableName]
            primaryCols = table.primary_key.columns
            # %%% Hack to avoid using auto-generated ids.
            if len(primaryCols) == 0 or primaryCols[0].autoincrement is True:
                # Just match on all columns.
                cond = None
                for colName in record:
                    if cond is None:
                        cond = (df[colName] == record[colName])
                    else:
                        cond = cond & (df[colName] == record[colName])
                if cond is not None:
                    df.drop(df[cond].index, inplace=True)
            else:
                cond = None
                for primaryCol in primaryCols:
                    primaryName = primaryCol.name
                    if cond is None:
                        cond = (df[primaryName] == record[primaryName])
                    else:
                        cond = cond & (df[primaryName] == record[primaryName])
                    #if tableName == "Taxon":
                    #    print("2 DROPPING %s: %r" % (tableName, cond))
                if cond is not None:
                    df.drop(df[cond].index, inplace=True)
                    #if tableName == "Taxon":
                    #    print("2 DROPPED %s: %r" % (tableName, record))

    def dumpToTarget(self, tableName, df):

        if self.targetDef.KIND == "db":

            # Apply any specified data filters.
            self.applyFilters(tableName, df)

            if tableName in self.opts.OMIT_COLUMNS_FOR_DB:
                columnsToOmit = self.opts.OMIT_COLUMNS_FOR_DB[tableName]
                df.drop(columns=columnsToOmit, inplace=True, errors='ignore')

            df.to_sql(tableName, con=self.engine, if_exists='append', index=False)
            self.load_last_id(self.metadata.tables["LastId"], self.metadata.tables[tableName])
        elif self.targetDef.KIND == "excel":
            df.to_excel(self.excelWriter, sheet_name=tableName, header=True, index=False)
        else:
            err("Unsupported target kind for conversion: %s" % self.targetDef.KIND)


