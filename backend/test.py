import os
import json
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser

if __name__ == '__main__':
    config = {
        "output_format": "json",
        "--gemini_api_key": os.getenv("GEMINI_API_KEY")
    }
    config_parser = ConfigParser(config)

    converter = PdfConverter(
        config=config_parser.generate_config_dict(),
        artifact_dict=create_model_dict(),
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer(),
        llm_service=config_parser.get_llm_service()
    )
    rendered = converter("sheet.pdf")
    with open("sheet.json", "w", encoding="utf-8") as f:
        json_string = rendered.model_dump_json(indent=2)
        f.write(json_string)