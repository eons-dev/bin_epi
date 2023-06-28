import os
import logging
import shutil
import jsonpickle
from pathlib import Path
import eons
from .CatalogCards import *
from .EmiFetchCallbackFunctor import *


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

		this.enableRollback = False

		this.result = {}

		this.fetchCallback = EmiFetchCallbackFunctor()


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
		this.functionSucceeded = True

		logging.info(f"Initiating Transaction {this.name} for {this.tomes}")

		cachedFunctors = this.executor.cachedFunctors
		logging.debug(f"Executing {this.builder}({', '.join([str(a) for a in this.args] + [k+'='+str(v) for k,v in this.kwargs.items()])})")
		if (this.builder in cachedFunctors):
			functor = cachedFunctors[this.builder]
		else:
			functor = this.executor.GetRegistered(this.builder, this.package_type)
			this.executor.cachedFunctors.update({this.builder: functor})

		this.functionSucceeded = True
		this.fetchCallback.executor = this.executor
		functor.callbacks.fetch = this.fetchCallback

		for tome in this.tomes:
			epitome = this.GetTome(tome)
			if (epitome.path is None):
					logging.error(f"Could not find files for {tome}.")
					continue
			
			epitomeMapping = {
				"id" : epitome.id,
				"name": epitome.name,
				"version": epitome.version,
				"project_path": epitome.path,
				"space": epitome.space,
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

			kwargs = this.kwargs
			if (not kwargs):
				kwargs = {}
			kwargs.update(epitomeMapping)
			kwargs.update(argMapping)

			functor.WarmUp(**kwargs)
			functor.result.data = jsonpickle.decode(epitome.space)

			if (this.undo):
				if (not functor.DidFunctionSucceed()):
					logging.debug(f"Skipping rollback for {tome}; it does not appear to be installed.")
					continue
				logging.info(f"Rolling back {functor.name} {tome}")
				functor.callMethod = "Rollback"
				functor.rollbackMethod = "Function"
			else:
				if (functor.DidFunctionSucceed()):
					logging.debug(f"Skipping installation for {tome}; it appears to be installed.")
					continue
				logging.info(f"Calling {functor.name} {tome}")
				functor.callMethod ="Function"
				functor.rollbackMethod = "Rollback"

			epitomeUpdate = epitomeMapping
			functor.result.data = eons.util.DotDict()
			functor(**kwargs)
			epitomeUpdate.space = jsonpickle.encode(functor.result.data)

			if (functor.result.code != 0):
				this.functionSucceeded = False
				break
		
			for key, value in epitomeUpdate.items():
				setattr(epitome, key, value)
				
			epitome.fetch_results = this.fetchCallback.GetFetchResultsAsJson()
			this.fetchCallback.Clear()
			this.catalog.add(epitome)


	# Open or download a Tome.
	# tomeName should be given without the "tome_" prefix
	# RETURNS an Epitome containing the given Tome's Path and details or None.
	def GetTome(this, tomeName, tomeType="tome"):
		return this.executor.GetTome(tomeName, tomeType=tomeType)
	