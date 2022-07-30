import os
import logging
import traceback
import platform
import shutil
import jsonpickle
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT
import eons as e
from .CatalogCards import *

#Merx are actions: things like "install", "update", "remove", etc.
#These should be stored on the online repo as merx_{merx.name}, e.g. merx_install, etc.
class Merx(e.UserFunctor):
    def __init__(this, name=e.INVALID_NAME()):
        super().__init__(name)

        this.requiredKWArgs = [
            "tomes", #emi cli arguments 2 and beyond
            "paths", #where to put things, as determined by EMI
        ]
        #executor and catalog are treated specially; see ValidateArgs(), below, for details.

        # For optional args, supply the arg name as well as a default value.
        this.optionalKWArgs = {}

        # Ease of use members
        this.transactionSucceeded = False
        this.rollbackSucceeded = False

    # Do stuff!
    # Override this or die.
    def Transaction(this):
        pass


    # RETURN whether or not the Transaction was successful.
    # Override this to perform whatever success checks are necessary.
    def DidTransactionSucceed(this):
        return this.transactionSucceeded


    # Undo any changes made by Transaction.
    # Please override this too!
    def Rollback(this):
        this.catalog.rollback() #removes all records created by *this (see: https://docs.sqlalchemy.org/en/14/orm/tutorial.html#rolling-back).


    # RETURN whether or not the Transaction was successful.
    # Override this to perform whatever success checks are necessary.
    def DidRollbackSucceed(this):
        return this.rollbackSucceeded


    # Hook for any pre-transaction configuration
    def PreTransaction(this):
        pass


    # Hook for any post-transaction configuration
    def PostTransaction(this):
        pass
    

    # Convert Fetched values to their proper type.
    # This can also allow for use of {this.val} expression evaluation.
    def EvaluateToType(this, value, evaluateExpression = False):
        if (isinstance(value, dict)):
            ret = {}
            for key, value in value.items():
                ret[key] = this.EvaluateToType(value)
            return ret

        elif (isinstance(value, list)):
            ret = []
            for value in value:
                ret.append(this.EvaluateToType(value))
            return ret

        else:
            if (evaluateExpression):
                evaluatedvalue = eval(f"f\"{value}\"")
            else:
                evaluatedvalue = str(value)

            #Check original type and return the proper value.
            if (isinstance(value, (bool, int, float)) and evaluatedvalue == str(value)):
                return value

            #Check resulting type and return a casted value.
            #TODO: is there a better way than double cast + comparison?
            if (evaluatedvalue.lower() == "false"):
                return False
            elif (evaluatedvalue.lower() == "true"):
                return True

            try:
                if (str(float(evaluatedvalue)) == evaluatedvalue):
                    return float(evaluatedvalue)
            except:
                pass

            try:
                if (str(int(evaluatedvalue)) == evaluatedvalue):
                    return int(evaluatedvalue)
            except:
                pass

            #The type must be a string.
            return evaluatedvalue


    # Wrapper around setattr
    def Set(this, varName, value):
        value = this.EvaluateToType(value)
        logging.debug(f"Setting ({type(value)}) {varName} = {value}")
        setattr(this, varName, value)


    # Will try to get a value for the given varName from:
    #    first: this
    #    second: the executor (args > config > environment)
    # RETURNS the value of the given variable or None.
    def Fetch(this,
        varName,
        default=None,
        enableThisMerx=True,
        enableThisExecutor=True,
        enableExecutorConfig=True,
        enableEnvironment=True):

        ret = this.executor.Fetch(varName, default, enableThisExecutor, False, enableExecutorConfig, enableEnvironment)

        if (enableThisMerx and hasattr(this, varName)):
            logging.debug(f"...got {varName} from self ({this.name}).")
            return getattr(this, varName)

        return ret


    # Override of eons.UserFunctor method. See that class for details.
    def ValidateArgs(this, **kwargs):
        # logging.debug(f"Got arguments: {kwargs}")
        setattr(this, 'executor', kwargs['executor'])
        setattr(this, 'catalog', kwargs['catalog'])

        for rkw in this.requiredKWArgs:
            if (hasattr(this, rkw)):
                continue

            if (rkw in kwargs):
                this.Set(rkw, kwargs[rkw])
                continue

            fetched = this.Fetch(rkw)
            if (fetched is not None):
                this.Set(rkw, fetched)
                continue

            # Nope. Failed.
            errStr = f"{rkw} required but not found."
            logging.error(errStr)
            raise MerxError(errStr)

        for okw, default in this.optionalKWArgs.items():
            if (hasattr(this, okw)):
                continue

            if (okw in kwargs):
                this.Set(okw, kwargs[okw])
                continue

            this.Set(okw, this.Fetch(okw, default=default))


    # Override of eons.Functor method. See that class for details
    def UserFunction(this, **kwargs):
        logging.info(f"Initiating Transaction {this.name} for {this.tomes}")

        this.PreTransaction()

        logging.debug(f"<---- {this.name} ---->")
        this.Transaction()
        logging.debug(f">----<")

        this.PostTransaction()

        if (this.DidTransactionSucceed()):
            logging.debug("Success :)")
        else:
            logging.error("Transaction did not succeed :(")


    # Open or download a Tome.
    # tomeName should be given without the "tome_" prefix
    # RETURNS an Epitome containing the given Tome's Path and details or None.
    def GetTome(this, tomeName):
        return this.executor.GetTome(tomeName)

    # RETURNS: an opened file object for writing.
    # Creates the path if it does not exist.
    def CreateFile(this, file, mode="w+"):
        Path(os.path.dirname(os.path.abspath(file))).mkdir(parents=True, exist_ok=True)
        return open(file, mode)


    # Run whatever.
    # DANGEROUS!!!!!
    # TODO: check return value and raise exceptions?
    # per https://stackoverflow.com/questions/803265/getting-realtime-output-using-subprocess
    def RunCommand(this, command):
        p = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True)
        while True:
            line = p.stdout.readline()
            if (not line):
                break
            print(line.decode('utf8')[:-1])  # [:-1] to strip excessive new lines.
