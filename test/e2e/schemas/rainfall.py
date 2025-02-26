NAME = "Rainfall"

ID = "Id"
DATE = "Date"
AMOUNT = "Amount"

KEY = ID

schema = TableSchema(
    NAME,
    {
        ID: DataType.AUTOID,
        DATE: DataType.DATE,
        AMOUNT: DataType.STRING,
    },
    KEY,
    [DATE]
)
