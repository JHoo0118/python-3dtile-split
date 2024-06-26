import json
from ifcopenshell.entity_instance import entity_instance
from utils import to_dict, extract_non_null_attributes

class BatchTableService(object):
    _instance = None
    exclude_keys: list[str] = ["representation", "objectPlacement", "ownerHistory"]

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)

        return cls._instance
        
    def init_batch_table_keys(self, project: entity_instance) -> tuple[dict, dict]:
        batch_table: dict = {
          "batchId": [],
        }
        batch_table_mapping = {}
        project_dict = to_dict(project, self.exclude_keys)
        for key in project_dict:
            if key in self.exclude_keys:
                continue
            batch_table[key] = []
        return batch_table, batch_table_mapping
    
    def create_batch_table(self, batch_table: dict[str, list], batch_table_mapping: dict, index: int, property: dict):
        batch_table["batchId"].append(index)
        mapping_key = property["globalId"] + str(index)
        batch_table_mapping[mapping_key] = {}
            
        for key in property:
          if key == "batchId":
              continue
          if key in batch_table:
            value = property[key]
            batch_table[key].append(value)
            batch_table_mapping[mapping_key][key] = value

        batch_table_mapping[mapping_key]["batchId"] = index

    def save_batch_table(self, output_dir: str, output_filename: str, batch_table: dict, batch_table_mapping: dict):
        with open(f'{output_dir}/{output_filename}_batch_table.json', 'w') as f:
            json.dump(batch_table, f, indent=2)
        with open(f'{output_dir}/{output_filename}_batch_table_mapping.json', 'w') as f:
            json.dump(batch_table_mapping, f, indent=2)