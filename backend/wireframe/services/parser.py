import logging
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
# We import Any to allow the return type hint without circular dependencies or specific package version lock-in
from typing import Any 

logger = logging.getLogger(__name__)

class DoclingService:
    def __init__(self):
        # Configure once
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False 
        pipeline_options.do_table_structure = False
        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = True
        pipeline_options.images_scale = 2.0 
        
        self.converter = DocumentConverter(
            format_options={
                "pdf": PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def parse_pdf(self, file_path: str) -> Any:
        """
        Parses the PDF and returns the DoclingDocument object.
        Returns 'Any' to avoid tight coupling with Docling's specific Pydantic model in the signature,
        but runtime object is strictly typed by Docling.
        """
        path_obj = Path(file_path)
        logger.info(f"Docling processing: {path_obj}")
        return self.converter.convert(path_obj).document
