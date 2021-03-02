from functools import partial
import pickle

class PickleFourSerializer:
    dumps = partial(pickle.dumps, protocol=4)
    loads = pickle.loads