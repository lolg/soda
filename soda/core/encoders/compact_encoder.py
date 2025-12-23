import json


class CompactArrayEncoder(json.JSONEncoder):
    """JSON encoder with readable formatting for long arrays."""
    
    def encode(self, obj):
        return self._encode_obj(obj, 0)
    
    def _encode_obj(self, obj, indent_level):
        indent = '  ' * indent_level
        next_indent = '  ' * (indent_level + 1)
        
        if isinstance(obj, dict):
            if not obj:
                return '{}'
            
            items = []
            for key, value in obj.items():
                key_str = json.dumps(key)
                value_str = self._encode_obj(value, indent_level + 1)
                items.append(f'{next_indent}{key_str}: {value_str}')
            
            return '{\n' + ',\n'.join(items) + '\n' + indent + '}'
            
        elif isinstance(obj, list):
            if not obj:
                return '[]'
            
            # Check if all items are simple types
            if all(isinstance(item, (int, str, float, bool, type(None))) for item in obj):
                # For long arrays, wrap every 10 items
                if len(obj) > 10:
                    items = [json.dumps(item) for item in obj]
                    wrapped_lines = []
                    
                    for i in range(0, len(items), 10):
                        chunk = items[i:i+10]
                        wrapped_lines.append(next_indent + ', '.join(chunk))
                    
                    return '[\n' + ',\n'.join(wrapped_lines) + '\n' + indent + ']'
                else:
                    # Short arrays stay on one line
                    items = [json.dumps(item) for item in obj]
                    return '[' + ', '.join(items) + ']'
            else:
                # Complex arrays get full multi-line treatment
                items = []
                for item in obj:
                    item_str = self._encode_obj(item, indent_level + 1)
                    items.append(f'{next_indent}{item_str}')
                
                return '[\n' + ',\n'.join(items) + '\n' + indent + ']'
        
        else:
            return json.dumps(obj)