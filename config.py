# Imports
from types import SimpleNamespace
from pathlib import Path
import yaml
import copy
import warnings
from typing import Any
import importlib

# Config
class Config(SimpleNamespace):

    debug: bool = False
    file: str = None

    @staticmethod
    def map_entry(entry):
        if isinstance(entry, dict):
          return Config(**entry)
        return entry

    @staticmethod
    def rev_map_entry(entry):
        if isinstance(entry, Config):
          return entry.to_dict_recursive()
        return entry

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for key, val in kwargs.items():
            if type(val) == dict:
                setattr(self, key, Config(**val))
            elif type(val) == list:
                setattr(self, key, list(map(self.map_entry, val)))

    def to_dict(self) -> dict:
        # Convert the Config to a dictionary
        return vars(self)
    
    def to_dict_recursive(self) -> dict:
        # Convert all Configs contained in this Config to dictionaries
        self = self.to_dict()
        for key, val in self.items():
            if isinstance(val, Config):
                self[key] = val.to_dict_recursive()
            elif isinstance(val, list):
                self[key] = list(map(Config.rev_map_entry, val))
        return self

    def create_instance(self, additional_kwargs: dict=None,
                        create_arg_instances: bool=True,
                        init_fn: str='__init__') -> object:
        # Convert to dictionary
        cfg = self.to_dict()
        # Load the module class
        Class, init_fn = self._get_module_class(next(iter(cfg)))
        # Get argments to provide to class
        kwargs = copy.deepcopy(next(iter(cfg.values())).to_dict())
        if create_arg_instances:
            # Check arguments for classes/instances that need to be loaded
            for k,v in kwargs.items():
                if isinstance(v, str) and '.' in v and '/' not in v:
                    kwargs[k] = self._get_module_class(v)
                elif isinstance(v, Config) and '.' in next(iter(v.to_dict().keys())):
                    kwargs[k] = v.create_instance()
                elif isinstance(v, list):
                    for i in range(len(v)):
                        if isinstance(v[i], str) and '.' in v[i] and '/' not in i:
                            v[i] = self._get_module_class(v[i])
                        elif isinstance(v[i], Config) and '.' in next(iter(v[i].to_dict().keys())):
                            v[i] = v[i].create_instance()
        # If additional/default arguments were provided from source code...
        if additional_kwargs:
            # Scan the additional arguments
            for k,v in additional_kwargs.items():
                # If they are already defined by user, warn
                if k in kwargs:
                    warnings.warn(f'During creation of {Class} instance, '
                                  f'default argument of {k} is being overriden by user. '
                                  f'Ensure this is what you intended!')
                # Else update arguments dictionary with additional argument
                else:
                    kwargs[k] = v
        if init_fn == '__init__':
            return Class(**kwargs)
        else:
            return getattr(Class, init_fn)(**kwargs)
    
    def _get_module_class(self, spec: str) -> Any:
        module_and_class = spec.split('.')
        clss = module_and_class[-1]
        mod = '.'.join(module_and_class[:-1])
        for _ in range(2): #HACK
            try: mod = importlib.import_module(mod); break
            except: pass
        if isinstance(mod, str): 
            raise self.ConfigError(f'Cant import module {mod}')
        elif not hasattr(mod, clss):
            raise self.ConfigError(f'Module {mod} has no class {clss}')
        Class = getattr(mod, clss)
        return Class

    def has(self, attr: str) -> bool:
        if (hasattr(self, attr) and
            getattr(self, attr) is not None):
            return True
        else:
            return False
        
    def __contains__(self, item: str) -> bool:
        return self.has(item)

    def keys(self):
        return self.to_dict().keys()
 
    def values(self):
        return self.to_dict().values()
        
    def items(self):
        return self.to_dict().items()

    @staticmethod
    def from_yaml(config_file: Path|str):
        if isinstance(config_file, str):
            config_file = Path(config_file)
            Config.file = config_file
        with open(config_file) as f:
            config_dict = yaml.load(f, Loader=yaml.FullLoader)
        cfg = Config(**config_dict)
        return cfg
    
    @staticmethod
    def from_yaml_string(yaml_str: str):
        cfg = Config(**yaml.safe_load(yaml_str))
        return cfg

    class ConfigError(Exception):
        """
        Error exception for configurations.
        """
        pass