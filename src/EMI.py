import os
import logging
import eons as e
import sqlalchemy as sql
from pathlib import Path
from .Exceptions import *
from .Epitome import *

class PathSelector:
    def __init__(this, name, systemPath):
        this.name = name
        this.systemPath = systemPath
        this.selectedPath = None

class EMI(e.Executor):

    def __init__(this):
        super().__init__(name="eons Module Installer", descriptionStr="A package manager for eons and infrastructure technologies.")

        #The library is where all Tomes are initially distributed from (i.e. the repo_store)
        #   and where records for all Tome locations and Merx Transactions are kept.
        this.library = Path.home().joinpath(".eons")

        #Windows paths must be set in the config.json.
        this.paths = [
            PathSelector("bin", "/usr/local/bin/"),
            PathSelector("inc", "/usr/local/include/"),
            PathSelector("lib", "/usr/local/lib/")
        ]

        this.sqlEngine = sql.create_engine(f"sqlite:///{str(this.library.joinpath('index.db'))}")
        this.sqlSession = sql.orm.sessionmaker(bind=this.sqlEngine)

    #Override of eons.Executor method. See that class for details
    def Configure(this):
        this.defaultRepoDirectory = str(this.library.joinpath("tmp"))
        this.defualtConfigFile = str(this.library.joinpath("config.json"))

    #Override of eons.Executor method. See that class for details
    def RegisterAllClasses(this):
        super().RegisterAllClasses()

    #Override of eons.Executor method. See that class for details
    def AddArgs(this):
        super().AddArgs()
        this.argparser.add_argument('merx', type = str, nargs=1, metavar = 'install or remove', help = 'what to do', dest = 'merx')
        this.argparser.add_argument('tomes', type = str, nargs='*', metavar = 'package_name', help = 'how to do it', dest = 'tomes')

    #Override of eons.Executor method. See that class for details
    def ParseArgs(this):
        super().ParseArgs()
        #NOTE: THERE SHOULD BE NO this.extraArgs

    #Override of eons.Executor method. See that class for details
    def UserFunction(this, **kwargs):
        if (not this.library.exists()):
            this.library.mkdir()
            this.library.joinpath("tmp").mkdir()
            this.library.joinpath("config.json").touch()
            this.library.joinpath("index.db").touch()
            ConstructCatalog(this.sqlEngine)

        super().UserFunction(**kwargs)
        
        #paths will be provided to the Merx as a dictionary.
        this.SelectPaths()
        paths = {}
        for path in this.paths:
            paths[path.name] = path.selectedPath

        transaction = TransactionLog(this.args.merx, '; '.join(this.args.tomes))
        try:
            merx = this.GetRegistered(this.args.merx, "merx")
            if (merx(tomes=this.args.tomes, paths=paths, catalog=this.sqlSession)):
                transaction.result = True
                logging.info(f"Complete.")
            else:
                merx.Rollback()
                transaction.result = False
                logging.error(f"Transaction failed!")
        except Exception as e:
            transaction.result = False
            logging.error("ERROR!")
            pass
        this.sqlSession.add(transaction)
        this.sqlSession.commit() #make sure the transaction log gets committed.

        #TODO: develop TransactionLog retention policy (i.e. trim records after 1 year, 1 day, or don't record at all).

    def SelectPaths(this):
        for path in this.paths:
            preferredPath = Path(this.Fetch(f"{path.name}_path", default=path.systemPath))
            if (preferredPath.exists() and os.access(str(preferredPath), os.W_OK | os.X_OK)):
                path.selectedPath = preferredPath
            else:
                path.selectedPath = this.library.joinpath(path.name)
                logging.debug(f"The preferred path for {path.name} ({str(preferredPath)}) was unusable.")
                path.path.mkdir(exist_ok=True)
            logging.debug(f"Path for {path.name} set to {str(path.selectedPath)}.")