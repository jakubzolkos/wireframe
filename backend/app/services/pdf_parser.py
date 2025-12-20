import io
from typing import Any
import fitz
from marker.convert import convert_single_pdf
from unstructured.partition.pdf import partition_pdf
from app.core.exceptions import PDFParsingError
from app.core.graph_state import PDFChunk
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PDFParserService:
    CONFIDENCE_THRESHOLD = 0.7

    async def parse_pdf(self, pdf_content: bytes, pdf_path: str) -> tuple[list[PDFChunk], str | None]:
        try:
            await logger.ainfo("pdf_parsing_start", pdf_path=pdf_path, size_bytes=len(pdf_content))
            chunks: list[PDFChunk] = []
            schematic_image_path: str | None = None

            try:
                chunks, confidence = await self._parse_with_marker(pdf_content, pdf_path)
                if confidence < self.CONFIDENCE_THRESHOLD:
                    await logger.awarn("marker_low_confidence", confidence=confidence, falling_back=True)
                    chunks = await self._parse_with_unstructured(pdf_content, pdf_path)
            except Exception as e:
                await logger.awarn("marker_parse_failed", error=str(e), falling_back=True)
                chunks = await self._parse_with_unstructured(pdf_content, pdf_path)

            schematic_image_path = await self._extract_schematic_image(pdf_content)

            await logger.ainfo("pdf_parsing_complete", chunks_count=len(chunks), has_schematic=schematic_image_path is not None)
            return chunks, schematic_image_path

        except Exception as e:
            await logger.aerror("pdf_parsing_error", error=str(e))
            raise PDFParsingError(f"Failed to parse PDF: {str(e)}") from e

    async def _parse_with_marker(self, pdf_content: bytes, pdf_path: str) -> tuple[list[PDFChunk], float]:
        pdf_file = io.BytesIO(pdf_content)
        result = convert_single_pdf(pdf_file, model="marker/marker-base")
        
        chunks: list[PDFChunk] = []
        confidence_sum = 0.0
        count = 0

        for page_num, page_content in enumerate(result.get("pages", []), start=1):
            text = page_content.get("text", "")
            confidence = page_content.get("confidence", 0.5)
            confidence_sum += confidence
            count += 1

            if text.strip():
                chunks.append(
                    PDFChunk(
                        content=text,
                        page_number=page_num,
                        section_title=page_content.get("section_title"),
                        chunk_type="marker",
                    )
                )

        avg_confidence = confidence_sum / count if count > 0 else 0.0
        return chunks, avg_confidence

    async def _parse_with_unstructured(self, pdf_content: bytes, pdf_path: str) -> list[PDFChunk]:
        pdf_file = io.BytesIO(pdf_content)
        elements = partition_pdf(file=pdf_file, strategy="hi_res")

        chunks: list[PDFChunk] = []
        current_page = 1
        current_text = ""

        for element in elements:
            page_num = getattr(element, "metadata", {}).get("page_number", current_page)
            if page_num != current_page and current_text:
                chunks.append(
                    PDFChunk(
                        content=current_text,
                        page_number=current_page,
                        chunk_type="unstructured",
                    )
                )
                current_text = ""
                current_page = page_num

            text = str(element)
            if text.strip():
                current_text += text + "\n"

        if current_text:
            chunks.append(
                PDFChunk(
                    content=current_text,
                    page_number=current_page,
                    chunk_type="unstructured",
                )
            )

        return chunks

    async def _extract_schematic_image(self, pdf_content: bytes) -> str | None:
        try:
            pdf_doc = fitz.open(stream=pdf_content, filetype="pdf")
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                text = page.get_text().lower()
                if any(keyword in text for keyword in ["typical application", "reference design", "schematic"]):
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    image_bytes = pix.tobytes("png")
                    await logger.ainfo("schematic_image_found", page=page_num + 1)
                    pdf_doc.close()
                    return f"schematic_page_{page_num + 1}.png"
            pdf_doc.close()
            return None
        except Exception as e:
            await logger.awarn("schematic_extraction_failed", error=str(e))
            return None


pdf_parser_service = PDFParserService()
