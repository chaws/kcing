import os
import logging
from datetime import datetime, timedelta

from peewee import SqliteDatabase, Model, DateTimeField, CharField
import settings

logger = logging.getLogger()
kcingdb = SqliteDatabase(settings.KCING_DB)

class BaseModel(Model):
    class Meta:
        database = kcingdb


class Object(BaseModel):
    # The combination _type + oid should be unique!
    _type = CharField(column_name='type')
    oid = CharField()
    created_on = DateTimeField(default=datetime.now)

tables = [Object,]


def create_tables():
    kcingdb.create_tables(tables)


def init():
    new_db = not os.path.isfile(settings.KCING_DB)
    if new_db:
        os.mknod(settings.KCING_DB)
        
    kcingdb.connect(reuse_if_open=True)

    if new_db: 
        create_tables()


def end():
    kcingdb.close()


def all_objs(_type):
    objs = set()
    for o in Object.select(Object.oid).where(Object._type == _type):
        objs.add(o.oid)
    return objs


def save(_type, objs):
    if len(objs) == 0:
        return 0

    prepared_data = []
    for _id in objs.keys():
        prepared_data.append({'_type': _type, 'oid': _id})

    with kcingdb.atomic():
        inserted = Object.insert_many(prepared_data).execute()

    return inserted


def delete_old(days=None):
    """
    The default number of days to keep lava/builds is 3. This is because
    we're retrieving the last two days worth of data from KernelCI. Take this as
    example: 
    Day 1: retrieved objects 1, 2 and 3
    Day 2: retrieved objects 2, 3, 4 and 5 (number of objects may vary)
    Day 3: retrieved objects 4, 5, and 6

    Note that in day 3, nor objects 1, 2 and 3 showed up. That's because
    they're too old and will never be retrieved again, in a normal scenario.

    If the number of days worth of data coming in increases, then the DRP_DAYS
    setting should be always one day greater than the first settings of days.
    """
    if days == 0:
        drp_datetime = datetime.now()
    else:
        drp_datetime = datetime.now() - timedelta(days=days or settings.DRP_DAYS)

    deleted = Object.delete().where(Object.created_on < drp_datetime).execute()
    logger.info('%i objects deleted' % (deleted))
    return deleted


# Facade to be called through command line
def drp(args):
    logger.info('Data Rentention Ploicy will clean up indices older than %i days in kcing.db' % (args.drp_days))
    deleted = delete_old(args.drp_days)
    return 0 if deleted >= 0 else -1
         
    
