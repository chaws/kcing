from peewee import SqliteDatabase, Model, DateField, CharField

kcidb = SqliteDatabase('kernelci.db')

class BaseModel(Model):
    class Meta:
        database = kcidb


class Boot(Model):
    oid = CharField()


class Build(Model):
    oid = CharField()
