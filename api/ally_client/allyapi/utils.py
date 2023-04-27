import re


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    @classmethod
    def from_nested_dicts(cls, data):
        """ Construct nested AttrDicts from nested dictionaries. """
        if not isinstance(data, dict):
            return data
        else:
            for k,v in data.items():
                new_v = v
                if type(v) is str:
                    if v == "false":
                        new_v = False
                    elif v == "true":
                        new_v = True
                    elif re.match(r'^[-+]?[?]?[0-9]*\.[0-9]+$',v):
                        new_v = float(v)
                    elif re.match(r'^[0-9]+$', v):
                        new_v = int(v)
                data[k] = new_v
            return cls({key: cls.from_nested_dicts(data[key]) for key in data})

