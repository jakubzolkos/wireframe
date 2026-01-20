import logging
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions

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

    def parse_pdf(self, file_path: Path):
        """Returns the Docling Document object"""
        logger.info(f"Docling processing: {file_path}")
        return self.converter.convert(file_path).document