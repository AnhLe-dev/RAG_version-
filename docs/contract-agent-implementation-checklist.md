# Checklist triển khai Contract Review Agent — từ trong ra ngoài

## Mục tiêu và phạm vi

Xây dựng một agent sử dụng LangChain để đọc hợp đồng liên quan đến thư tín dụng, truy xuất tài liệu nội bộ như UCP600, đối chiếu điều khoản và trả kết quả có citation cùng vị trí highlight trên hợp đồng.

Thứ tự triển khai: **Dữ liệu → Logic xử lý → Tools → Agent → Service → API → Giao diện.**

Nền tảng hiện có theo `backendphase1.md`: RAG Basic với ingestion UCP600, embedding, Qdrant, dense retrieval, generation, citation validator và API hỏi đáp. Đây là trạng thái theo tài liệu mô tả, chưa phải kết quả kiểm tra code thực tế.

Các mục dưới đây là công việc đề xuất bổ sung. Bản đầu dùng một agent; chưa cần tự thiết kế LangGraph hoặc MAS.

## 1. Dữ liệu hợp đồng

- [ ] Định nghĩa `ContractDocument`: ID hợp đồng, tên file, phiên bản hoặc checksum, trạng thái xử lý và vị trí lưu file gốc.
- [ ] Định nghĩa `ContractClause`: ID điều khoản, ID hợp đồng, số điều hoặc nhãn, nguyên văn và thứ tự xuất hiện.
- [ ] Lưu trang và tọa độ nguồn cho từng đoạn; một điều khoản có thể nằm ở nhiều trang.
- [ ] Phân biệt dữ liệu hợp đồng cần review với tài liệu knowledge dùng làm căn cứ.

**Hoàn thành khi:** mỗi điều khoản truy ngược được về đúng vị trí trong file gốc.

## 2. Đọc và lưu hợp đồng

- [ ] Lưu PDF gốc và tạo `contract_id`.
- [ ] Trích xuất text cùng trang, ID đoạn và tọa độ.
- [ ] Nhận diện ranh giới và số thứ tự điều khoản hợp đồng.
- [ ] Giữ nguyên văn để đối chiếu và hiển thị.
- [ ] Lưu kết quả xử lý và trạng thái: đang xử lý, sẵn sàng hoặc lỗi.
- [ ] Giới hạn bản đầu ở PDF có text; báo rõ khi PDF scan chưa được hỗ trợ.

**Hoàn thành khi:** đọc được một hợp đồng mẫu và lấy đúng điều khoản 4 hoặc 5 cùng vị trí nguồn.

**Lưu ý:** tái sử dụng phần đọc PDF khi phù hợp. Không áp dụng nguyên parser UCP600 yêu cầu 39 Article và bố cục hai cột cho hợp đồng.

## 3. Truy xuất điều khoản hợp đồng

- [ ] Viết hàm lấy điều khoản theo `contract_id` và số điều hoặc ID điều khoản.
- [ ] Trả nguyên văn, ID đoạn, trang và tọa độ.
- [ ] Cho phép lấy ngữ cảnh liên quan khi cần.
- [ ] Phân biệt rõ không tìm thấy hợp đồng và không tìm thấy điều khoản.

**Hoàn thành khi:** lấy đúng điều khoản hoặc trả trạng thái không tìm thấy rõ ràng.

## 4. Truy xuất knowledge

- [ ] Tận dụng embedding và dense retrieval hiện có.
- [ ] Nhận câu hỏi, nội dung điều khoản và phạm vi tài liệu cần đối chiếu.
- [ ] Lọc đúng tài liệu, phiên bản và phạm vi truy cập do backend kiểm soát.
- [ ] Trả bằng chứng gồm ID, nguyên văn, nguồn, phiên bản, số điều và vị trí.
- [ ] Xử lý trường hợp chưa tìm thấy căn cứ phù hợp.
- [ ] Kiểm tra cấu hình `access_scope`: API hiện được mô tả là cố định `public`, trong khi mục tiêu là knowledge nội bộ.

**Hoàn thành khi:** truy xuất được bằng chứng có nguồn rõ ràng cho một điều khoản mẫu.

**Lưu ý:** tách retrieval để trả bằng chứng; không bọc toàn bộ `RagService.ask()` thành tool tìm kiếm. Không tìm thấy qua retrieval chưa chứng minh rằng kho hoàn toàn không có kiến thức liên quan.

## 5. Đọc đầy đủ điều khoản tham chiếu

- [ ] Viết hàm lấy toàn văn theo ID tài liệu, phiên bản và số điều.
- [ ] Trả các đoạn theo đúng thứ tự, không thiếu hoặc lặp nội dung.
- [ ] Giữ thông tin nguồn và vị trí cho nội dung trả về.
- [ ] Phân biệt rõ số điều trong hợp đồng và số điều trong UCP600.

**Hoàn thành khi:** có thể mở đầy đủ điều khoản tham chiếu khi một chunk tìm kiếm chưa đủ ngữ cảnh.

## 6. Schema kết quả review

- [ ] Định nghĩa `ReviewFinding`: ID điều khoản hoặc đoạn hợp đồng, trạng thái, lý do và các ID bằng chứng.
- [ ] Định nghĩa `ReviewResult`: câu trả lời, phạm vi đã kiểm tra và danh sách findings.
- [ ] Quy định các trạng thái: phát hiện không phù hợp; chưa phát hiện không phù hợp trong phạm vi kiểm tra; chưa đủ căn cứ.
- [ ] Phân biệt lỗi xử lý hoặc không tìm thấy điều khoản với kết quả compliance.
- [ ] Giữ tham chiếu tới đoạn hợp đồng để backend ánh xạ vị trí highlight.

**Hoàn thành khi:** đầu ra có cấu trúc thống nhất để kiểm tra và hiển thị.

## 7. Kiểm tra kết quả và bằng chứng

- [ ] Kiểm tra ID đoạn hợp đồng tồn tại và thuộc đúng hợp đồng đang review.
- [ ] Kiểm tra citation trỏ tới bằng chứng thực sự được tool trả về.
- [ ] Kiểm tra đoạn trích khớp với nguồn đã lưu.
- [ ] Kiểm tra các trường bắt buộc trong kết quả.
- [ ] Không chấp nhận kết luận không phù hợp thiếu đoạn hợp đồng hoặc căn cứ hỗ trợ.
- [ ] Quy định xử lý khi validation thất bại: sửa có giới hạn hoặc trả lỗi rõ ràng.

**Hoàn thành khi:** phát hiện được nguồn không tồn tại, trích dẫn sai nguyên văn và dữ liệu thiếu.

**Giới hạn:** validator kiểm tra nhãn citation tồn tại chưa chứng minh bằng chứng hỗ trợ kết luận. Cần đánh giá quan hệ giữa nhận định và bằng chứng bằng các trường hợp review có đáp án chuẩn.

## 8. Bọc logic thành tools

- [ ] `get_contract_clauses`: gọi logic ở bước 3 để lấy điều khoản hợp đồng.
- [ ] `search_knowledge`: gọi logic ở bước 4 để tìm bằng chứng.
- [ ] `get_reference_clause`: gọi logic ở bước 5 để đọc đầy đủ căn cứ.
- [ ] Định nghĩa schema đầu vào và đầu ra cho mỗi tool.
- [ ] Viết mô tả rõ mục đích, khi nào dùng và các trường hợp không tìm thấy.
- [ ] Kiểm tra từng tool độc lập trước khi nối vào agent.

**Hoàn thành khi:** ba tool chạy độc lập và trả dữ liệu có cấu trúc, có nguồn.

## 9. Agent LangChain

- [ ] Kết nối model, system prompt, ba tool và schema đầu ra.
- [ ] Cấu hình model riêng cho agent; lựa chọn dự kiến là GPT-4o, trong khi Phase 1 đang mô tả `gpt-4o-mini`.
- [ ] Phân biệt yêu cầu hỏi nội dung hợp đồng với yêu cầu kiểm tra compliance.
- [ ] Yêu cầu truy xuất căn cứ trước khi đánh giá compliance.
- [ ] Kiểm tra đủ ngữ cảnh và cơ sở áp dụng bộ quy tắc trước khi kết luận.
- [ ] Hỏi lại nếu người dùng không nói rõ điều khoản thuộc tài liệu nào.
- [ ] Trả chưa đủ căn cứ khi thiếu thông tin, không suy diễn thành phù hợp.
- [ ] Xem nội dung tài liệu là dữ liệu phân tích, không phải chỉ dẫn điều khiển agent.
- [ ] Thiết lập giới hạn lượt gọi tool, timeout và xử lý lỗi.

**Hoàn thành khi:** agent lấy đúng điều khoản, tìm căn cứ, đối chiếu và trả kết quả có nguồn cho một yêu cầu mẫu.

## 10. Service điều phối

- [ ] Nhận câu hỏi, `contract_id` và phạm vi knowledge.
- [ ] Kiểm tra quyền truy cập và trạng thái sẵn sàng của hợp đồng.
- [ ] Gọi agent và chạy validator trên kết quả.
- [ ] Ánh xạ ID đoạn sang tọa độ highlight đã lưu.
- [ ] Ghi log cần thiết để theo dõi lỗi và các tool đã gọi.
- [ ] Trả kết quả hoặc lỗi theo cấu trúc thống nhất.

**Hoàn thành khi:** hoàn thành một yêu cầu review từ đầu đến cuối mà chưa cần giao diện.

## 11. API

- [ ] Endpoint upload hợp đồng và trả `contract_id`.
- [ ] Endpoint lấy trạng thái xử lý hợp đồng.
- [ ] Endpoint xem hoặc tải PDF gốc theo quyền truy cập.
- [ ] Endpoint hỏi hoặc review theo `contract_id`.
- [ ] Response chứa findings, citation và thông tin highlight.
- [ ] Xử lý hợp đồng chưa sẵn sàng, không tìm thấy, không có quyền và lỗi dịch vụ.

**Hoàn thành khi:** gọi được luồng upload → review → nhận findings qua API.

## 12. Frontend và highlight

- [ ] Giao diện upload và hiển thị trạng thái xử lý.
- [ ] Ô nhập câu hỏi gắn với hợp đồng đang chọn.
- [ ] Hiển thị PDF gốc.
- [ ] Hiển thị kết quả review, nguyên văn hợp đồng và citation.
- [ ] Cho phép bấm finding để chuyển tới đúng trang và highlight.
- [ ] Hiển thị riêng đoạn hợp đồng được review và căn cứ từ knowledge.

**Hoàn thành khi:** người dùng xem được nhận định và đúng đoạn hợp đồng liên quan.

**Lưu ý:** tọa độ UCP600 không thay thế tọa độ hợp đồng upload. Bản đầu có thể highlight theo block; muốn chính xác từng câu cần dữ liệu vị trí chi tiết hơn. Model chọn ID đoạn, không tự đoán tọa độ.

## Kiểm thử nghiệm thu toàn luồng

- [ ] Hỏi nội dung một điều khoản có thật.
- [ ] Hỏi điều khoản không tồn tại.
- [ ] Review trường hợp có bằng chứng rõ ràng.
- [ ] Review trường hợp thiếu căn cứ hoặc thiếu ngữ cảnh.
- [ ] Xử lý câu hỏi mơ hồ giữa điều khoản hợp đồng và tài liệu tham chiếu.
- [ ] Phát hiện citation tồn tại nhưng không hỗ trợ kết luận trong bộ đánh giá.
- [ ] Highlight đúng vị trí trên hợp đồng.
- [ ] Xử lý nội dung tài liệu chứa chỉ dẫn đánh lừa agent.
- [ ] Ngăn truy cập hợp đồng hoặc knowledge ngoài phạm vi được phép.
- [ ] Xử lý timeout, tool lỗi và giới hạn lượt gọi tool.

## Mốc triển khai

| Mốc | Phạm vi | Kết quả cần đạt |
|---|---|---|
| 1 | Bước 1–3 | Đọc, lưu và lấy đúng điều khoản hợp đồng kèm vị trí |
| 2 | Bước 4–5 | Tìm và đọc đầy đủ căn cứ knowledge |
| 3 | Bước 6–8 | Có schema, validator và ba tool chạy độc lập |
| 4 | Bước 9–10 | Một agent review hoàn chỉnh qua service |
| 5 | Bước 11–12 | Upload, hỏi/review, citation và highlight qua giao diện |

**Bắt đầu ngay:** hoàn thành bước 1–2 với một PDF mẫu, xác nhận từng điều khoản giữ được nguyên văn, trang và tọa độ.

BM25, reranker, LangGraph và MAS là các hướng mở rộng sau khi luồng đầu tiên đã được kiểm chứng.
