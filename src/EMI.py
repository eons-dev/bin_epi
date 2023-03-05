import os
import logging
import eons
import sqlalchemy as sql
import sqlalchemy.orm as orm
from pathlib import Path
from eot import EOT
from .Exceptions import *
from .CatalogCards import *

class PathSelector:
	def __init__(this, name, systemPath):
		this.name = name
		this.systemPath = systemPath
		this.selectedPath = None

class EMI(eons.Executor):

	def __init__(this):

		# The library is where all Tomes are initially distributed from (i.e. the repo_store)
		#   and where records for all Tome locations and Merx Transactions are kept.
		# We need to create these files for there to be a valid config.json to read from. Otherwise, eons.Executor crashes.
		this.library = Path.home().joinpath(".eons")
		this.sqlEngine = sql.create_engine(f"sqlite:///{str(this.library.joinpath('catalog.db'))}")
		this.catalog = orm.sessionmaker(bind=this.sqlEngine)() # sqlalchemy: sessionmaker()->Session()->session.
		this.SetupHome()

		super().__init__(name="Eons Modular Interface", descriptionStr="A universal state manager.")

		# Windows paths must be set in the config.json.
		this.paths = [
			PathSelector("exe", "/usr/local/bin/"),
			PathSelector("inc", "/usr/local/include/"),
			PathSelector("lib", "/usr/local/lib/")
		]
		
		# Ease of use method for processed paths.
		this.selectedPaths = {}

	# Create initial resources if they don't already exist.
	def SetupHome(this):
		if (not this.library.exists()):
			logging.info(f"Creating home folder: {str(this.library)}")
			this.library.mkdir()
			this.library.joinpath("tmp").mkdir()

		catalogFile = this.library.joinpath("catalog.db")
		if (not catalogFile.exists()):
			logging.info(f"Creating catalog: {str(catalogFile)}")
			catalogFile.touch()
		if (not catalogFile.stat().st_size):
			logging.info("Constructing catalog scheme")
			ConstructCatalog(this.sqlEngine)

		configFile = this.library.joinpath("config.json")
		if (not configFile.exists() or not configFile.stat().st_size):
			logging.info(f"Initializing config file: {str(configFile)}")
			config = open(configFile, "w+")
			config.write("{\n}")


	# Override of eons.Executor method. See that class for details
	def Configure(this):
		super().Configure()
		this.tomeDirectory = this.library.joinpath("tmp")
		this.defaultRepoDirectory = str(this.library.joinpath("merx"))
		this.defaultConfigFile = str(this.library.joinpath("config.json"))
		this.defaultPackageType = "merx"

	# Override of eons.Executor method. See that class for details
	def RegisterAllClasses(this):
		super().RegisterAllClasses()

	# Override of eons.Executor method. See that class for details
	def AddArgs(this):
		super().AddArgs()
		this.argparser.add_argument('merx', type=str, metavar='merx', help='what to do (e.g. \'install\' or \'remove\')')
		this.argparser.add_argument('tomes', type=str, nargs='*', metavar='tome', help='how to do it (e.g. \'my_package\')')

	# Override of eons.Executor method. See that class for details
	def ParseArgs(this):
		super().ParseArgs()
		# NOTE: THERE SHOULD BE NO this.extraArgs

	# Override of eons.Executor method. See that class for details
	def Function(this):

		super().Function()
		
		# paths will be provided to each Merx as a dictionary.
		this.SelectPaths()
		merxList = this.parsedArgs.merx.split('/')
		
		this.Execute(merxList.pop(0), next=merxList)

	def SelectPaths(this):
		for path in this.paths:
			preferredPath = Path(this.Fetch(f"{path.name}_path", default=path.systemPath))
			if (preferredPath.exists() and os.access(str(preferredPath), os.W_OK | os.X_OK)):
				path.selectedPath = preferredPath
			else:
				path.selectedPath = this.library.joinpath(path.name)
				logging.debug(f"The preferred path for {path.name} ({str(preferredPath)}) was unusable.")
				path.selectedPath.mkdir(exist_ok=True)
			this.selectedPaths[path.name] = path.selectedPath
			logging.debug(f"Path for {path.name} set to {str(path.selectedPath)}.")
			
	def Execute(this, merx, *args, **kwargs):
		transaction = TransactionLog(merx, '; '.join(this.parsedArgs.tomes))
		transaction.result = super().Execute(merx, *args, tomes=this.parsedArgs.tomes, paths=this.selectedPaths, catalog=this.catalog, **kwargs)
		this.catalog.add(transaction)
		
		# make sure the transaction log gets committed.
		# TODO: develop TransactionLog retention policy (i.e. trim records after 1 year, 1 day, or don't record at all).
		this.catalog.commit()

	# GetRegistered modified for use with Tomes.
	# tomeName should be given without the ".tome" suffix
	# RETURNS an Epitome containing the given Tome's Path and details or None.
	def GetTome(this, tomeName, tomeType="tome", download=True):
		logging.debug(f"Fetching {tomeName}.{tomeType}.")

		tomePath = this.tomeDirectory.joinpath(f"{tomeName}.{tomeType}")
		logging.debug(f"Will place {tomeName} in {tomePath}.")

		epitome = this.catalog.query(Epitome).filter(Epitome.name==tomeName).first()
		if (epitome is None):
			epitome = Epitome(tomeName)
			if (not download):
				logging.warning(f"Epitome for {tomeName} did not exist and will not be downloaded.")
		else:
			logging.debug(f"Got exiting Epitome for {tomeName}.")

		if (tomePath.exists()):
			logging.debug(f"Found {tomeName} on the local filesystem.")
			epitome.path = tomePath
		elif (download):
			preservedRepo = this.repo['store']
			preservedUrl = this.repo['url']
			if (epitome.retrieved_from is not None and len(epitome.retrieved_from)):
				this.repo['url'] = epitome.retrieved_from
			this.repo['store'] = str(this.tomeDirectory)
			logging.debug(f"Attempting to download {tomeName} from {this.repo['url']}")
			this.DownloadPackage(packageName=f"{tomeName}.{tomeType}", registerClasses=False, createSubDirectory=True)
			if (tomePath.exists()):
				epitome.path = tomePath
				epitome.retrieved_from = this.repo['url']
				if (epitome.first_retrieved_on is None or epitome.first_retrieved_on == 0):
					epitome.first_retrieved_on = EOT.GetStardate()
				epitome.last_retrieved_on = EOT.GetStardate()
				if (epitome.version is None):
					epitome.version = ""
					# TODO: populate epitome.version. Blocked by https://github.com/infrastructure-tech/srv_infrastructure/issues/2
			else:
				logging.error(f"Failed to download {tomeName}.{tomeType}")

			this.repo['url'] = preservedUrl
			this.repo['store'] = preservedRepo
		else:
			logging.warning(f"Could not find {tomeName}; only basic info will be available.")

		return epitome
