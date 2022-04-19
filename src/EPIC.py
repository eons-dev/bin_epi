import os
import logging
import eons as e
from .Exceptions import *

class EPIC(e.Executor):

    def __init__(this):
        super().__init__(name="eons Package Infrastructure Controller", descriptionStr="A package manager for eons and infrastructure technologies.")

        this.RegisterDirectory("epic")

    #Override of eons.Executor method. See that class for details
    def RegisterAllClasses(this):
        super().RegisterAllClasses()

    #Override of eons.Executor method. See that class for details
    def AddArgs(this):
        super().AddArgs()
        this.argparser.add_argument('-i', 'install', type = str, action='append', nargs='*', metavar = 'package_mine', help = 'install a package', dest = 'install')
        this.argparser.add_argument('-u','update', type = str, action='append', nargs='*', metavar = 'package_mine', help = 'update a package', dest = 'update')
        this.argparser.add_argument('-r','remove', type = str, action='append', nargs='*', metavar = 'package_mine', help = 'remove a package (aka uninstall)', dest = 'remove')


    #Override of eons.Executor method. See that class for details
    def ParseArgs(this):
        super().ParseArgs()

    #Override of eons.Executor method. See that class for details
    def UserFunction(this, **kwargs):
        super().UserFunction(**kwargs)
        this.Execute(this.args.builder, this.args.path, this.args.build_in, this.events, **this.extraArgs)

    #Install a package
    def Install(this, packageName):
        pass

    #Install a package
    def Update(this, packageName):
        pass

    #Install a package
    def Remove(this, packageName):
        pass