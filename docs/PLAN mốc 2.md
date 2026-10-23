# Kế hoạch Mốc 2 — Tìm và đọc đầy đủ căn cứ UCP600

## 1. Mục tiêu

Mốc 2 nhận một điều khoản đã hoàn thành ở Mốc 1, trước mắt là `LC01 / 47A.2`, rồi thực hiện hai việc:

1. Tìm các chunk UCP600 có liên quan, kèm nguồn, phiên bản, Article, trang và `bbox`.
2. Từ một kết quả tìm kiếm, lấy toàn văn Article UCP600 tương ứng theo đúng thứ tự nguồn.

Luồng dự kiến:

```text
contract_id + label 47A.2
  -> ContractClauseRetrievalService
  -> câu hỏi + nguyên văn 47A.2
  -> embedding
  -> Qdrant lọc đúng scope/source/version
  -> evidence chunks
  -> chọn Article 16
  -> đọc toàn văn Article 16 từ UCP600.pdf
```

Mốc này chưa sinh kết luận compliance, chưa gọi ChatGPT để trả lời và chưa tạo LangChain tool.

## 2. Các bước triển khai

### Bước 1 — Hoàn thiện model bằng chứng knowledge

- Mở rộng `RetrievedChunk` để giữ lại:
  - `source_checksum_sha256`;
  - `source_spans`;
  - `parent_chunk_id`.
- Tạo `ReferenceClause` gồm source ID, version, checksum, Article, title, nguyên văn, page range, source spans và access scope.
- Dùng lại `SourceSpan`; không tạo kiểu tọa độ thứ hai.

Lý do: payload Qdrant đã chứa các trường này, nhưng model hiện tại bỏ qua chúng nên Mốc 2 chưa thể trả vị trí nguồn.

### Bước 2 — Lọc đúng tài liệu trong Qdrant

- Sửa dense retrieval để bắt buộc lọc đồng thời:
  - `access_scope`;
  - `source_id`;
  - `source_version`.
- Tạo keyword payload index cho cả ba trường.
- Hợp nhất hai định nghĩa `ensure_collection()` đang trùng trong `qdrant_store.py`.
- Thêm script chỉ tạo/kiểm tra payload index, không embed lại 199 chunks.

Lý do: collection hiện chỉ chứa UCP600 nhưng service vẫn phải xác định đúng tài liệu và phiên bản; không được dựa vào giả định collection sẽ mãi chỉ có một nguồn.

### Bước 3 — Tạo Knowledge Retrieval Service

Public interface:

```python
search_contract_clause(
    *,
    question: str,
    clause: ContractClause,
    access_scope: str,
    source_id: str = "ucp600",
    source_version: str = "1",
) -> tuple[RetrievedChunk, ...]
```

Service sẽ:

1. Validate câu hỏi, scope, source và clause.
2. Tạo query text từ câu hỏi, label, title và nguyên văn clause.
3. Embed query một lần.
4. Search Qdrant với `final_top_n`.
5. Trả evidence theo thứ tự score, không gọi LLM.
6. Trả tuple rỗng nếu không có kết quả; không tự kết luận rằng knowledge không có quy định liên quan.

Lý do dùng cả câu hỏi và clause: câu hỏi thể hiện mục tiêu pháp lý, còn nguyên văn clause giữ thuật ngữ cụ thể như “discrepancy fee”.

### Bước 4 — Tạo Reference Clause Service

Public interface:

```python
get_article(
    *,
    source_id: str,
    source_version: str,
    article_number: int,
    access_scope: str,
) -> ReferenceClause
```

Service sẽ:

1. Chuẩn bị corpus từ file `UCP600.pdf` bằng parser hiện tại.
2. Kiểm tra source ID, version, checksum và scope.
3. Tìm đúng `LegalArticle`.
4. Ghép body block theo reading order.
5. Trả toàn văn cùng title, page range và source spans.
6. Phân biệt:
   - source/version/scope không khả dụng;
   - Article không tồn tại.

Lý do đọc từ PDF/corpus gốc: top-k Qdrant chỉ là đoạn tìm kiếm, không bảo đảm chứa toàn bộ Article và không được dùng để giả lập toàn văn.

### Bước 5 — Tạo hai smoke script độc lập

- Script tìm căn cứ:
  - input: `contract_id`, label và câu hỏi;
  - lấy `47A.2` từ PostgreSQL;
  - tìm UCP600 evidence;
  - in đầy đủ text, score, Article, page và bbox.
- Script đọc Article:
  - input: số Article;
  - lấy toàn văn Article từ corpus;
  - in source/version/checksum rút gọn, title, page range và spans.

Câu hỏi nghiệm thu live:

```text
What UCP 600 provision governs refusal due to discrepancies?
```

Kết quả mong đợi: top-k có Article 16; đây là tiêu chí retrieval, chưa phải kết luận rằng phí USD77 phù hợp hay không.

### Bước 6 — Kiểm thử và khóa nghiệm thu

Kiểm thử offline:

- Parser UCP600 vẫn đạt 39 Article, 136 paragraph, 197 item và 199 chunk.
- Qdrant result giữ nguyên checksum và source spans.
- Filter luôn chứa đúng scope/source/version.
- Query text chứa cả câu hỏi và nguyên văn contract clause.
- Article 16 được trả đủ block, đúng thứ tự, không lặp.
- Sai source, version, scope hoặc Article trả đúng lỗi.
- Không làm hỏng retrieval/API RAG hiện tại.

Kiểm thử live:

- Tạo đủ ba payload index mà không re-embed.
- Tìm từ `LC01 / 47A.2`, top-k chứa Article 16.
- Mọi result đều có `source_id=ucp600`, `source_version=1`, đúng scope và có bbox.
- Lấy được toàn văn Article 16 từ PDF nguồn.
- Không gọi answer model và không phát sinh chi phí generation.

## 3. Cách chúng ta sẽ làm từng bước

Bạn sẽ tự tạo/cập nhật file. Với mỗi bước, mình sẽ gửi theo đúng cấu trúc:

1. File cần tạo hoặc sửa.
2. Khối code để copy.
3. Từng import dùng để làm gì.
4. Input → logic → output.
5. Lý do chọn thiết kế đó.
6. Lệnh kiểm tra không chứa secret.
7. Output mong đợi.

Chỉ khi bạn gửi kết quả pass của bước hiện tại, chúng ta mới chuyển sang bước tiếp theo.

## 4. Giới hạn đã chốt

- Mốc 2 chỉ hỗ trợ UCP600 nhưng interface giữ `source_id/source_version` để mở rộng sau.
- Dùng LC01 `47A.2` làm ca kiểm chứng chính.
- Giữ `access_scope="public"` trong smoke script; service vẫn bắt buộc nhận và kiểm tra scope.
- Không thêm API, agent, LangChain tool, review schema hoặc kết luận compliance trong Mốc 2.
- Không đọc hoặc in value thật trong `.env`.
- Không re-embed/reindex vector nếu payload hiện tại đã đủ; chỉ bổ sung payload index.
