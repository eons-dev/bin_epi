import eons

# All Merx errors
class MerxError(Exception, metaclass=eons.ActualType): pass

# Exception used for miscellaneous Merx errors.
class OtherMerxError(MerxError, metaclass=eons.ActualType): pass
