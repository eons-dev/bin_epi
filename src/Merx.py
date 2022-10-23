import os
import logging
import shutil
from pathlib import Path
import eons
from .CatalogCards import *

#Merx are actions: things like "install", "update", "remove", etc.
#These should be stored on the online repo as merx_{merx.name}, e.g. merx_install, etc.
class Merx(eons.Functor):
    def __init__(this, name=eons.INVALID_NAME()):
        super().__init__(name)

        this.requiredKWArgs = [
            "tomes", #emi cli arguments 2 and beyond
            "paths", #where to put things, as determined by EMI
        ]
        #executor and catalog are treated specially; see ValidateArgs(), below, for details.

        # For optional args, supply the arg name as well as a default value.
        this.optionalKWArgs = {}

        this.transactionSucceeded = False


    # Do stuff!
    # Override this or die.
    def Transaction(this):
        pass


    # Undo any changes made by Transaction.
    # Please override this too!
    def Rollback(this):
        this.catalog.rollback() #removes all records created by *this (see: https://docs.sqlalchemy.org/en/14/orm/tutorial.html#rolling-back).


    # RETURN whether or not the Transaction was successful.
    # While you can override this, it is preferred that you simply set this.transactionSucceeded throughout Transaction().
    def DidTransactionSucceed(this):
        return this.transactionSucceeded


    # API compatibility shim with eons.Functor method.
    def DidFunctionSucceed(this):
        this.functionSucceeded = this.transactionSucceeded
        return this.DidTransactionSucceed()


    # RETURN whether or not the Rollback was successful.
    # While you can override this, it is preferred that you simply set this.rollbackSucceeded
    # Override of eons.Functor method.
    def DidRollbackSucceed(this):
         return this.rollbackSucceeded


    # Hook for any pre-transaction configuration
    def PreTransaction(this):
        pass


    # Hook for any post-transaction configuration
    def PostTransaction(this):
        pass


    # Grab any known and necessary args from kwargs before any Fetch calls are made.
    # Override of eons.Functor method.
    def ParseInitialArgs(this):
        super().ParseInitialArgs()
        setattr(this, 'catalog', this.kwargs['catalog'])


    # Override of eons.Functor method. See that class for details
    def Function(this):
        logging.info(f"Initiating Transaction {this.name} for {this.tomes}")

        this.PreTransaction()
        this.Transaction()
        this.PostTransaction()


    # Open or download a Tome.
    # tomeName should be given without the "tome_" prefix
    # RETURNS an Epitome containing the given Tome's Path and details or None.
    def GetTome(this, tomeName):
        return this.executor.GetTome(tomeName)
