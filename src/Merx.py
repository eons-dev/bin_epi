import os
import logging
import shutil
from pathlib import Path
import eons
from .CatalogCards import *


# Merx are actions: things like "install", "update", "remove", etc.
# These should be stored on the online repo as merx_{merx.name}, e.g. merx_install, etc.
class Merx(eons.StandardFunctor):
	def __init__(this, name=eons.INVALID_NAME()):
		super().__init__(name)

		this.requiredKWArgs = [
			"builder", # which builder to use for given tomes (must be builder name not builder object)
			"tomes", # emi cli arguments 2 and beyond
			"paths", # where to put things, as determined by EMI
		]
		# executor and catalog are treated specially; see ValidateArgs(), below, for details.

		# For optional args, supply the arg name as well as a default value.
		this.optionalKWArgs["undo"] = False
		this.optionalKWArgs["package_type"] = "build"

		this.functionSucceeded = False
		this.enableRollback = False

		this.result = {}


	# Undo any changes made by Transaction.
	# Please override this too!
	def Rollback(this):
		super().Rollback()
		this.catalog.rollback() # removes all records created by *this (see: https://docs.sqlalchemy.org/en/14/orm/tutorial.html# rolling-back).


	# Grab any known and necessary args from kwargs before any Fetch calls are made.
	# Override of eons.Functor method.
	def ParseInitialArgs(this):
		super().ParseInitialArgs()
		setattr(this, 'catalog', this.kwargs['catalog'])


	# Override of eons.Functor method. See that class for details
	def Function(this):
		logging.info(f"Initiating Transaction {this.name} for {this.tomes}")

		cachedFunctors = this.executor.cachedFunctors
		logging.debug(f"Executing {this.builder}({', '.join([str(a) for a in this.args] + [k+'='+str(v) for k,v in this.kwargs.items()])})")
		if (this.builder in cachedFunctors):
			functor = cachedFunctors[this.builder]
		else:
			functor = this.executor.GetRegistered(this.builder, this.package_type)
			this.executor.cachedFunctors.update({this.builder: functor})

		for tome in this.tomes:
			epitome = this.GetTome(tome)

			if (epitome.installed_at is not None and len(epitome.installed_at) and epitome.installed_at != "NOT INSTALLED"):
				logging.debug(f"Skipping installation for {tome}; it appears to be installed.")
				continue
			
			if (epitome.path is None):
				logging.error(f"Could not find files for {tome}.")
				continue

			epitomeMapping = {
				"id" : epitome.id,
				"name": epitome.name,
				"version": epitome.version,
				"project_path": epitome.path,
				"installed_at": epitome.installed_at,
				"retrieved_from": epitome.retrieved_from,
				"first_retrieved_on": epitome.first_retrieved_on,
				"last_retrieved_on": epitome.last_retrieved_on,
				"additional_notes": epitome.additional_notes
			}

			argMapping = {
				"paths": this.paths,
				"path": this.executor.library.joinpath("tmp"),
				"build_in": "build",
				"events": this.executor.events,
				"executor": this.executor
			}

			kwargs = kwargs.update(epitomeMapping)
			kwargs = kwargs.update(argMapping)

			functor.WarmUp(*args, **kwargs)

			epitomeUpdate = epitomeMapping

			if (this.undo):
				epitomeUpdate.update(dict(functor.Rollback()))
			else:
				epitomeUpdate.update(dict(functor.Function()))

			if (not functor.functionSucceeded):
				this.functionSucceeded = False
				break
		
			if (this.functionSucceeded):
				for key, value in epitomeUpdate.items():
					setattr(epitome, key, value)
					
				this.catalog.add(epitomeUpdate)


	# Open or download a Tome.
	# tomeName should be given without the "tome_" prefix
	# RETURNS an Epitome containing the given Tome's Path and details or None.
	def GetTome(this, tomeName, tomeType="tome"):
		return this.executor.GetTome(tomeName, tomeType=tomeType)
