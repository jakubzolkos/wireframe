import os
import json
from pathlib import Path
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser

if __name__ == '__main__':
    sheet_pdf_path = Path(__file__).parent.parent / "sheet.pdf"
    fixture_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    rendered = converter(str(sheet_pdf_path))
    
    fixture_path = fixture_dir / "sheet_pdf_rendered.json"
    
    if hasattr(rendered, 'model_dump'):
        output = rendered.model_dump()
    elif hasattr(rendered, 'dict'):
        output = rendered.dict()
    else:
        output = {"rendered": str(rendered)}
    
    with open(fixture_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"Fixture saved to {fixture_path}")


