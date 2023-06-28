import eons
import os
import logging
import platform
import shutil
import jsonpickle
import sqlalchemy as sql
import sqlalchemy.orm as orm
from sqlalchemy import ForeignKey
from pathlib import Path
from eot import EOT
from .Exceptions import *

# CatalogCards are classes which will be stored in the catalog.db
SQLBase = orm.declarative_base()

# The Epitome class is an object used for tracking the location, status, and other metadata of a Tome package.
# epi = above, so metadata of a tome would be above a tome, would be epitome. Note that the "tome" portion of epitome actually derives from the word for "to cut". Epitome roughly means an abridgement or surface incision. Abridgement is appropriate here.
# Epitomes should not be extended when creating packages. They are only to be used by Merx for tracking existing packages.
class Epitome(SQLBase):
	__tablename__ = 'tomes'
	id = sql.Column(sql.Integer, primary_key=True)
	name = sql.Column(sql.String)
	version = sql.Column(sql.String) # not all versions follow Semantic Versioning.
	space = sql.Column(sql.String) # JSON string describing installation location details
	fetch_results = sql.Column(sql.String) # array of stored fetch callbacks
	retrieved_from = sql.Column(sql.String) # repo url
	first_retrieved_on = sql.Column(sql.Float) # startdate (per eot).
	last_retrieved_on = sql.Column(sql.Float) # startdate (per eot).
	additional_notes = sql.Column(sql.String) # TODO: Let's convert this to PickleType and store any user-defined values.

	path = None

	def __repr__(this):
		return f"<Epitome(id={this.id}, name={this.name}, version={this.version}, space={this.space}, retrieved_from={this.retrieved_from}, retrieved_on={this.retrieved_on}, additional_notes={this.additional_notes})>"

	def __init__(this, name=None):
		this.name = name


# Transaction logs are recorded whether or not the associated Merx.Transaction() completed.
class TransactionLog(SQLBase):
	__tablename__ = 'transactions'
	id = sql.Column(sql.Integer, primary_key=True)
	when = sql.Column(sql.Float)  # startdate (per eot).
	merx = sql.Column(sql.String) # name of merx
	tomes = sql.Column(sql.String) # semicolon-separated list of tome arguments
	result = sql.Column(sql.Integer) # return value of Merx.DidTransactionSucceed()

	def __init__(this, merx, tomes):
		this.when = EOT.GetStardate()
		this.merx = merx
		this.tomes = tomes


# This is here just to ensure all SQLBase children are created before *this is called.
# TODO: Can we move this into EMI?
def ConstructCatalog(engine):
	SQLBase.metadata.create_all(engine)
