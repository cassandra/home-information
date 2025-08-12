import logging


class SuppressPipelineTemplateVarsFilter(logging.Filter):
    """Filter out Django Pipeline template variable lookup errors."""

    PIPELINE_VARIABLES = {
        'media', 'title', 'charset', 'defer', 'async', 'rel'
    }

    def filter(self, record):
        # Check the log record for Pipeline-related template errors
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            
            # Check for Pipeline template path in the message
            if "pipeline/" in msg:
                return False
            
            # Check for common Pipeline variable lookup errors
            if "Failed lookup for key" in msg:
                # Extract variable name and check if it's a Pipeline variable
                import re
                match = re.search(r"Failed lookup for key \[(\w+)\]", msg)
                if match and match.group(1) in self.PIPELINE_VARIABLES:
                    return False
            
            # Check for Pipeline variable resolution errors
            if "Exception while resolving variable" in msg:
                for var_name in self.PIPELINE_VARIABLES:
                    if f"variable '{var_name}'" in msg:
                        return False
        
        # Also check if the record has template information
        if hasattr(record, 'exc_info') and record.exc_info:
            # Look at the traceback to see if it mentions pipeline templates
            import traceback
            tb_str = ''.join(traceback.format_exception(*record.exc_info))
            if 'pipeline/' in tb_str:
                return False
        
        return True