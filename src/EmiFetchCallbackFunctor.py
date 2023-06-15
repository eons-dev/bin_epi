from eons import FetchCallbackFunctor
import jsonpickle

class EmiFetchCallbackFunctor(FetchCallbackFunctor):

    def __init__(this, name = "EmiFetchCallbackFunctor"):
        super().__init__(name)

        this.fetchResults = []

    def Function(this):
        this.fetchResults.append({
            'varName' : str(this.varName),
            'location' : str(this.location),
            'value' : str(this.value)
        })
        return

    def GetFetchResultsAsJson(this):
        return jsonpickle.encode(this.fetchResults)

    def Clear(this):
        this.fetchResults = []