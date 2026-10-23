# Hướng dẫn Codex triển khai đánh giá pipeline RAG

## 1. Nhiệm vụ và phạm vi

Bạn là Codex làm việc trong repository của người dùng. Hãy triển khai bộ đánh giá pipeline RAG theo từng bước, đồng thời giải thích để người dùng hiểu code và tự review được.

Đối tượng đánh giá: câu hỏi → retrieval → context thực sự đưa vào LLM → câu trả lời.

- Giai đoạn đầu: RAG Basic với structure-aware chunking và dense retrieval.
- Giai đoạn sau: dùng lại bộ đánh giá để so sánh BM25 + Dense → RRF → Reranker.
- Backend dự kiến dùng Python, LangChain, FastAPI; frontend Next.js; dự án có Docker. Phải xác minh cấu trúc thực tế trước khi sửa.
- Chỉ triển khai evaluation cho RAG. Không mở rộng sang compliance agent, tool calling, phân loại hồ sơ, highlight PDF, frontend, reflection loop hoặc đánh giá toàn hệ thống.
- Không cần CI/CD hoặc quality gate trong phiên bản đầu.
- Tài liệu này là yêu cầu thiết kế, không khẳng định các file/service bên dưới đã tồn tại.

## 2. Cách làm việc và giải thích bắt buộc

### 2.1. Trước khi tạo hoặc sửa mỗi file

Giải thích bằng tiếng Việt:

1. **Vấn đề:** nếu chưa có file/thay đổi này thì đang thiếu điều gì?
2. **Trách nhiệm:** file làm gì và không chịu trách nhiệm gì?
3. **Đầu vào → xử lý → đầu ra:** dùng tên dữ liệu cụ thể.
4. **Liên kết:** module nào gọi file này, file này gọi module nào?
5. **Lý do lựa chọn:** tại sao tạo file riêng hoặc mở rộng file sẵn có?

Không chỉ nói “để code sạch hơn”. Nêu lợi ích cụ thể như tránh chạy lại RAG khi chấm lại, bảo vệ đáp án chuẩn, hoặc cô lập API Ragas.

### 2.2. Sau từng khối code trong câu trả lời hoặc tài liệu

Ngay sau khối code phải có:

- **Giải thích:** code làm gì, dữ liệu đi qua đâu, kết quả là gì?
- **Tại sao chọn cách này:** lý do kỹ thuật và trade-off liên quan.
- **Cách kiểm tra:** lệnh hoặc kết quả quan sát được khi phù hợp.

Quy tắc áp dụng cho Python, shell, JSON, YAML, cấu hình và ví dụ CLI. Không để nhiều khối code nối tiếp rồi giải thích chung ở cuối. Với code ghi trực tiếp vào file, giải thích theo file và theo các hàm/khối logic quan trọng trong bản bàn giao; không cần dán lại toàn bộ file dài hoặc bình luận từng dòng hiển nhiên.

### 2.3. Thứ tự và tính trung thực

- Đọc quy tắc repository, dependency, settings và RAG service trước.
- Triển khai theo các bước bên dưới; kiểm tra bước hiện tại trước khi chuyển bước phụ thuộc.
- Nếu người dùng chỉ yêu cầu một bước, giới hạn trong bước đó. Nếu yêu cầu toàn bộ, tiếp tục các bước đã được cho phép; không hỏi xác nhận cho từng file.
- Phân biệt: dữ kiện đã kiểm chứng, quyết định thiết kế, ví dụ minh họa và điều chưa xác minh.
- Không đoán tên hàm, import hoặc phiên bản API. Kiểm tra trong môi trường và tài liệu chính thức đúng phiên bản.
- Không thêm framework, interface, repository pattern hoặc lớp abstraction nếu chưa giải quyết một nhu cầu cụ thể.
- Không dùng dữ liệu giả để báo cáo rằng RAG thật đã chạy thành công.
- Thiếu credentials hoặc nguồn để duyệt đáp án: báo rõ giới hạn, tiếp tục các phần độc lập; không bịa kết quả.

## 3. Vai trò tài liệu

| Tài liệu | Vai trò ở phiên bản đầu | Giới hạn |
| --- | --- | --- |
| UCP600 | Knowledge base và nguồn bằng chứng chuẩn | Kiểm tra thứ tự đọc hai cột, điều/khoản và phiên bản |
| FAQ600 | Tham khảo chọn câu hỏi và soạn đáp án nháp | Bản đã cung cấp là scan; OCR và đối chiếu ảnh trước khi duyệt |
| LC01 | Chưa dùng | Tránh trộn đánh giá RAG với đọc hồ sơ và compliance |

Chỉ đưa vào bộ đề trả lời được những câu có căn cứ đủ trong UCP600. Không coi FAQ là quy tắc thay thế UCP600. Nếu sau này thêm FAQ vào knowledge base, ghi thành cấu hình corpus mới và báo cáo riêng.

Không ingestion dataset evaluation, đáp án chuẩn hoặc báo cáo vào vector database. Việc knowledge chứa căn cứ đúng là cần thiết; việc đưa nguyên bộ đề và đáp án vào knowledge làm sai mục tiêu kiểm thử độc lập.

## 4. Kế hoạch file và vấn đề từng file giải quyết

Các đường dẫn dưới đây là đề xuất tương đối từ repository root. Điều chỉnh theo cấu trúc thực tế, không tạo module trùng chức năng. Nếu cần `__init__.py`, giải thích nó dùng để xác lập package/import theo cách chạy đã chọn.

| File hoặc vị trí | Vấn đề giải quyết | Dữ liệu vào → dữ liệu ra | Lý do tách |
| --- | --- | --- | --- |
| `backend/evaluation/README.md` | Người dùng không biết chạy và đọc kết quả thế nào | Quy trình đã triển khai → hướng dẫn có lệnh thật | Giữ cách vận hành cạnh code |
| `backend/evaluation/schemas.py` | Mỗi bước hiểu khác nhau về cấu trúc dữ liệu | Object thô → test case/run record/score record hợp lệ | Một hợp đồng dữ liệu chung |
| `backend/evaluation/dataset.py` | Dataset sai, trùng ID hoặc lẫn placeholder đi vào chấm | JSONL → danh sách case hợp lệ | Validation trước khi tốn chi phí API |
| `backend/data/evaluation/ucp600/dev.jsonl` | Không có bộ đề ổn định để đo và sửa RAG | Nhãn đã duyệt → test case | Tách chuẩn đánh giá khỏi kết quả model |
| `backend/data/evaluation/ucp600/draft.jsonl` nếu cần | Nhãn chưa duyệt bị nhầm thành ground truth | Câu nháp → dữ liệu chờ duyệt | Chỉ tạo khi thực sự có bản nháp |
| `backend/evaluation/adapter.py` | Đầu ra RAG hiện tại không khớp đầu vào evaluation | Câu hỏi → response/context/IDs | Cô lập tích hợp với service thật |
| `backend/evaluation/runner.py` | Chạy thủ công mất trace và không tái lập được | Dataset + adapter → predictions + manifest | Tách chạy RAG khỏi chấm điểm |
| `backend/evaluation/judge.py` | Khởi tạo giám khảo rải rác, khó giữ cấu hình ổn định | Settings → judge LLM và embedding nếu metric cần | Dùng chung cấu hình giám khảo |
| `backend/evaluation/scoring.py` | Ghép trường sai hoặc lệ thuộc API Ragas ở nhiều nơi | Dataset + predictions → điểm từng metric | Một nơi ánh xạ API theo phiên bản |
| `backend/evaluation/report.py` | Điểm trung bình che lỗi từng câu và mẫu thất bại | Scores + manifest → báo cáo Markdown/CSV | Tách tính điểm và trình bày |
| `backend/evaluation_runs/<run_id>/` | Kết quả các lần chạy bị ghi đè/lẫn nhau | Kết quả thực chạy → artifact theo run | So sánh và truy vết |
| File dependency/settings hiện có | Thiếu dependency hoặc cấu hình riêng cho eval | Cấu hình môi trường → giá trị có validation | Tái sử dụng chuẩn dự án |

Không tạo tất cả file rỗng từ đầu. Tạo theo bước khi có trách nhiệm thực tế. Nếu cấu trúc hiện có phù hợp hơn, giải thích mapping và dùng lại.

## 5. Bước 0 — Khảo sát repository và điểm tích hợp

### Công việc

1. Đọc `AGENTS.md` và quy tắc engineering thực sự có trong repository.
2. Xác định dependency manager, phiên bản Python, package root và cách chạy backend.
3. Tìm đường đi từ API/service nhận câu hỏi đến retriever, context assembly và generator.
4. Xác định sync/async, kiểu dữ liệu response, nơi có context cuối, metadata của chunk.
5. Kiểm tra cách chọn pipeline Basic/Advanced và cách load settings.

### Kết quả cần báo cáo

- File/hàm cụ thể sẽ được gọi, kèm đường dẫn.
- Context cuối có sẵn hay phải bổ sung trace tối thiểu.
- Kế hoạch file mới/sửa và lý do từng file.

### Điều kiện hoàn thành

Biết rõ cách gọi pipeline thật và cách lấy context thực sự đưa vào LLM. Không dựng một RAG thay thế chỉ để evaluation chạy được.

## 6. Bước 1 — Chuẩn bị dataset chuẩn

### Công việc

1. Tạo schema và loader tối thiểu.
2. Bắt đầu với 3 câu để kiểm tra định dạng; sau đó mở rộng lên 10 câu đã duyệt.
3. Phân bố đề xuất cho 10 câu: 5 câu một điều/khoản, 3 câu điều kiện/ngoại lệ, 2 câu nhiều điều/khoản.
4. Chọn bằng chứng UCP600 trước, viết câu hỏi và đáp án sau; kiểm tra mọi ý trong đáp án được bằng chứng hỗ trợ.
5. Nếu không có tài liệu nguồn hoặc chưa xác minh đáp án, chỉ tạo draft. Không tuyên bố dataset là ground truth đã duyệt.

### Hợp đồng dữ liệu

| Trường | Kiểu đề xuất | Ý nghĩa |
| --- | --- | --- |
| `case_id` | string | ID duy nhất, ổn định |
| `user_input` | string | Câu hỏi thực gửi vào RAG |
| `reference` | string | Đáp án chuẩn được duyệt |
| `reference_contexts` | list[string] | Đoạn nguyên văn hỗ trợ đáp án |
| `reference_evidence_ids` | list[string] | ID nguồn điều/khoản ổn định |
| `category` | enum/string giới hạn | `single_clause`, `conditional`, `multi_clause` |
| `review_status` | enum | `draft` hoặc `reviewed` |

`reference_evidence_ids` và `review_status` là trường của dự án, không mặc định là trường Ragas. Có thể lưu vị trí trang và phiên bản nguồn trong metadata khi dự án đã hỗ trợ; không bịa số trang.

Ví dụ cấu trúc minh họa, không được dùng làm mẫu đã duyệt:

```json
{"case_id":"ucp600_001","user_input":"<câu hỏi>","reference":"<đáp án đã đối chiếu>","reference_contexts":["<nguyên văn nguồn>"],"reference_evidence_ids":["<ID điều/khoản>"],"category":"single_clause","review_status":"draft"}
```

**Giải thích:** mỗi dòng JSONL là một case độc lập. Các dấu giữ chỗ cho thấy cấu trúc, chưa chứa nội dung nghiệp vụ thật. `reference_contexts` là bằng chứng chuẩn, khác `retrieved_contexts` sẽ xuất hiện khi RAG chạy.

**Tại sao chọn cách này:** JSONL dễ review diff, đọc từng dòng và gắn lỗi với vị trí cụ thể. ID căn cứ theo nguồn giúp so sánh khi thay chunking; chunk ID có thể thay đổi giữa các phiên bản index.

**Cách kiểm tra:** loader phải báo dòng lỗi JSON, ID trùng, trường rỗng, kiểu sai và mẫu chưa duyệt khi chạy chế độ đánh giá thật. Ví dụ placeholder này phải bị từ chối trong chế độ đó.

### Điều kiện hoàn thành

- Dev dataset có 10 câu đã duyệt hoặc báo rõ số câu thực có và phần còn thiếu.
- Không có `response` hay `retrieved_contexts` do tự điền trong bộ đề.
- Không tự động ghi đè nhãn chuẩn bằng kết quả model.
- Khi mở rộng, tạo tập test giữ riêng; các biến thể cùng câu/tình huống ở cùng split. Không chỉnh prompt liên tục theo tập test.

## 7. Bước 2 — Chuẩn hóa đầu ra pipeline bằng adapter

### Công việc

1. Gọi service RAG hiện có, ưu tiên service layer dùng chung với ứng dụng.
2. Chỉ truyền câu hỏi và các tùy chọn runtime được phép. Không truyền đáp án chuẩn hoặc bằng chứng chuẩn vào generator/retriever.
3. Thu `response`, `retrieved_contexts`, `retrieved_context_ids` và cấu hình pipeline.
4. Đo latency bằng đồng hồ monotonic; ghi lỗi có cấu trúc.

### Yêu cầu trace

- `retrieved_contexts` phải là văn bản đúng sau lọc, rerank và cắt theo token budget mà generator nhận.
- Giữ thứ tự context; mỗi ID phải khớp đoạn text tương ứng.
- Nếu context bị cắt ngắn, lưu phiên bản đã cắt dùng thực tế.
- Không gọi retriever lần hai để tái dựng context sau khi đã sinh câu trả lời.
- Có thể lưu candidate retrieval riêng để chẩn đoán, nhưng không thay context cuối bằng candidates khi chấm câu trả lời.
- Nếu RAG chưa expose context, thêm trace nội bộ tối thiểu; không thay hành vi trả lời chỉ để tăng điểm.

### Vì sao chọn adapter

Runner chỉ cần một hợp đồng đầu ra ổn định. Khi service thay đổi, sửa adapter thay vì sửa dataset, scoring và report. Không cần tạo hierarchy nhiều lớp chỉ cho một adapter.

### Điều kiện hoàn thành

Một câu thực chạy trả về câu trả lời và context xác thực. Kiểm tra không có reference bị truyền vào pipeline. Nếu thiếu API key, kiểm tra mapping bằng fixture có nhãn rõ ràng và báo chưa chạy live.

## 8. Bước 3 — Viết runner và lưu kết quả

### Công việc

1. Đọc dataset đã validate.
2. Chạy tuần tự ở phiên bản đầu để dễ debug; chỉ thêm concurrency có giới hạn khi cần.
3. Tạo `run_id` duy nhất; lưu một record cho mỗi case, kể cả lỗi.
4. Ghi kết quả từng case sau khi hoàn thành để giảm mất dữ liệu khi tiến trình dừng.
5. Tách kết quả chạy khỏi dataset gốc.

### Artifact của mỗi lần chạy

| Artifact | Vấn đề giải quyết | Nội dung |
| --- | --- | --- |
| `predictions.jsonl` | Cần chấm lại mà không gọi RAG lại | case ID, response, contexts, IDs, latency, trạng thái, lỗi |
| `manifest.json` | Không biết kết quả được tạo từ cấu hình nào | run ID, thời gian, commit nếu có, dataset hash/version, corpus/index snapshot, prompt, model, cấu hình retrieval |
| `scores.jsonl` | Cần biết từng metric thành công hay thất bại | case ID, metric name, value, trạng thái, lỗi và lý do nếu API trả về |
| `report.md` | Người dùng cần hiểu kết quả | Tổng hợp, lỗi, câu cần xem và giới hạn |
| `scores.csv` nếu cần | Cần lọc/sắp xếp nhanh | Bảng điểm và trạng thái từng câu |

Không ghi secret vào manifest. Khi chưa có usage/cost thực, dùng null hoặc ghi là không có dữ liệu; không bịa con số. Nếu có ước tính, tách riêng và nêu phương pháp.

### Điều kiện hoàn thành

Chạy 5 câu tạo đủ 5 record. Một case lỗi không khiến các case khác biến mất. Lần chạy khác không ghi đè kết quả cũ. Chưa gọi Ragas ở bước này.

## 9. Bước 4 — Kết nối Ragas và chấm bốn metric

### Kiểm tra dependency trước

- Kiểm tra phiên bản Ragas và dependency tương thích với dự án.
- Khóa phiên bản đã kiểm chứng bằng cơ chế dự án đang dùng; không nâng toàn bộ LangChain tùy tiện.
- Đọc tài liệu chính thức tương ứng phiên bản. Không trộn collections API và legacy API theo các tutorial khác nhau.
- Xác minh chữ ký hàm, cơ chế sync/async và kiểu kết quả; chỉ dùng `ascore`/`.value` khi đúng API được cài.
- `build_judge` hoặc `score_dataset` trong đề xuất là hàm dự án cần triển khai, không mặc định là API của Ragas.

### Metric khởi đầu

| Metric | Dữ liệu logic cần dùng | Câu hỏi đo lường |
| --- | --- | --- |
| Context Precision có reference | user_input, retrieved_contexts, reference | Đoạn hữu ích có đứng cao trong danh sách không? |
| Context Recall dùng LLM | reference, retrieved_contexts; thêm user_input nếu API yêu cầu | Context hỗ trợ được bao nhiêu ý của đáp án chuẩn? |
| Faithfulness | response, retrieved_contexts; thêm trường API yêu cầu | Nhận định trong câu trả lời có căn cứ trong context không? |
| Answer Relevancy | user_input, response; judge và embedding theo API | Câu trả lời có đúng trọng tâm không? |

Đây là mô tả dữ liệu logic, không phải cam kết chữ ký API ở mọi phiên bản. Context Precision của Ragas có xét thứ hạng; Context Recall dùng LLM không phải phép đếm recall theo ID. Bốn metric không đủ chứng minh đáp án đúng hoàn toàn. Factual Correctness hoặc recall theo evidence ID là mở rộng sau baseline, không bắt buộc ở vòng đầu.

### Công việc

1. Tái sử dụng settings hiện có; thêm cấu hình judge model, embedding nếu cần, timeout và concurrency.
2. Judge và generator là hai vai trò riêng. Có thể dùng cùng nhà cung cấp/model, nhưng cấu hình và log riêng; không tuyên bố giám khảo độc lập nếu dùng cùng model.
3. Ghép dataset và predictions bằng `case_id`, không ghép theo thứ tự dòng. Kiểm tra thiếu/thừa/trùng ID và dataset hash/version.
4. Chỉ chuyển các trường đúng yêu cầu metric; giữ metadata dự án ngoài payload API nếu không được hỗ trợ.
5. Chạy một metric trên một case trước; sau đó đủ bốn metric trên 3–5 case.
6. Lưu trạng thái từng metric. Timeout, exception hoặc NaN phải được ghi là lỗi/không hợp lệ, không đổi thành 0 hoặc âm thầm bỏ qua.
7. Retry có giới hạn cho lỗi tạm thời; không retry vô hạn với schema sai hay cấu hình không hợp lệ.

### Vì sao tách scoring khỏi runner

Có thể chấm lại cùng predictions với logic mới mà không tạo câu trả lời mới. Điều này giúp phân biệt thay đổi của RAG và thay đổi của giám khảo. Lưu mỗi lần chấm riêng hoặc có scoring ID để không ghi đè mất lịch sử.

### Điều kiện hoàn thành

Có điểm thật cho các mẫu chạy thành công và trạng thái rõ cho các mẫu lỗi. Đọc thủ công vài câu để kiểm tra điểm có hợp lý, đặc biệt câu hỏi tiếng Việt với căn cứ tiếng Anh. Không công bố điểm mock là baseline.

## 10. Bước 5 — Báo cáo baseline và phân tích lỗi

### Báo cáo bắt buộc

- Số case dự kiến, số RAG chạy thành công, số chấm thành công theo từng metric.
- Điểm từng câu và trung bình theo metric/category, kèm số mẫu hợp lệ làm mẫu số.
- Danh sách lỗi runtime/scoring riêng.
- Latency của RAG tách khỏi latency chấm điểm.
- Câu có điểm thấp và đường dẫn trace để xem câu hỏi, response, reference, context.
- Cấu hình và phiên bản liên quan từ manifest.
- Giới hạn: dataset nhỏ, nhãn còn hạn chế hoặc chưa kiểm tra độ ổn định của judge.

Không gộp bốn metric thành một điểm “accuracy” tùy ý. Không dùng mức 0.85/0.80/0.75 trong đề xuất làm tiêu chuẩn legal hoặc production.

| Hiện tượng | Kiểm tra trước khi sửa |
| --- | --- |
| Recall thấp | Căn cứ có trong corpus/index không, thứ tự đọc đúng không, chunk bị cắt không, filter/top-k có phù hợp không |
| Precision thấp | Query, chunk trùng/nhiễu, ranking, context budget |
| Faithfulness thấp | Chấm đúng context chưa, câu trả lời thêm nhận định nào, context có đủ để trả lời không |
| Relevancy thấp | Có trả lời thẳng yêu cầu không, có lạc đề không |
| Điểm tốt nhưng đáp án vẫn sai | Kiểm tra thủ công độ đúng/đủ, nhãn chuẩn và hạn chế của các metric |

### Điều kiện hoàn thành

Baseline Basic có thể tái lập từ dataset/config đã lưu. Nêu giả thuyết lỗi kèm case cụ thể; không suy từ một metric thấp ra một nguyên nhân duy nhất.

## 11. Bước 6 — So sánh với Advanced RAG khi đã sẵn sàng

Chỉ thực hiện khi baseline Basic chạy ổn và người dùng yêu cầu bước nâng cấp/so sánh. Không tự xây Advanced RAG chỉ vì tài liệu này có bước so sánh.

| Thử nghiệm | Cấu hình |
| --- | --- |
| A | Dense retrieval |
| B | Dense + BM25 + RRF |
| C | Cấu hình B + reranker |

Giữ dataset, corpus snapshot, generator, prompt và judge giống nhau. Giữ ngân sách context cuối tương đương hoặc giải thích sự khác biệt. Ghi riêng candidate pool và top-k cuối. Nếu chunking cũng thay đổi, coi đó là một biến thử nghiệm khác.

So sánh theo cùng `case_id`, báo độ thay đổi từng metric và latency. Nếu số case hợp lệ khác nhau, nêu rõ và báo cả tập chung; không so hai trung bình với mẫu số khác nhau như thể cùng điều kiện. Nếu chênh lệch nhỏ, kiểm tra độ dao động bằng chạy lặp trên các case liên quan trước khi kết luận.

## 12. Kiểm tra kỹ thuật cần thiết

Chọn kiểm tra có ý nghĩa theo rủi ro, không viết test chỉ để sao chép implementation:

- Loader từ chối JSON hỏng, ID trùng, trường rỗng, placeholder hoặc draft ở chế độ đánh giá thật.
- Adapter không nhận/truyền reference vào RAG; context được lấy từ trace thật.
- Ghép case theo ID vẫn đúng khi thứ tự predictions thay đổi.
- Case thất bại được giữ trong kết quả; không coi NaN là điểm 0.
- Report đếm đúng số mẫu hợp lệ và lỗi cho từng metric.
- Smoke test API thực với tập nhỏ khi có credentials; mock/fixture chỉ kiểm tra logic tích hợp và phải ghi rõ.

Tái sử dụng test framework của repository. Không chạy bộ chấm LLM tốn phí cho mọi unit test. Không bắt buộc Docker service mới; có thể dùng môi trường backend hoặc eval dependency group phù hợp repo.

## 13. Mẫu bàn giao sau mỗi bước

1. Đã giải quyết vấn đề gì.
2. File tạo/sửa: đường dẫn, trách nhiệm và lý do.
3. Code quan trọng: giải thích ngay sau từng khối theo mục 2.
4. Luồng gọi thực tế: điểm vào → hàm/module tiếp theo → output.
5. Lệnh chạy đã kiểm chứng, thư mục chạy và cấu hình cần có; giải thích ngay sau khối lệnh.
6. Kết quả kiểm tra thực tế; phân biệt live và mock, nêu phần chưa chạy.
7. Điều kiện hoàn thành đạt/chưa đạt và bước tiếp theo.

Hướng dẫn người dùng mở file nào trước để review, rồi đi theo một luồng dữ liệu cụ thể. Không yêu cầu họ đọc tất cả module cùng lúc.

## 14. Tài liệu tham khảo để Codex đối chiếu khi triển khai

- Bài hướng dẫn người dùng cung cấp: https://www.datacamp.com/vi/tutorial/rag-evaluation-with-ragas
- Ragas migration: https://docs.ragas.io/en/stable/howtos/migrations/migrate_from_v03_to_v04/
- Context Precision: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/
- Context Recall: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/
- Faithfulness: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/
- Answer Relevancy: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/

Các URL `stable` có thể đổi theo thời gian. Dùng tài liệu và mã nguồn đúng phiên bản cài đặt; tài liệu này không thay thế việc kiểm tra API trong repository.

## 15. Chỉ dẫn bắt đầu

Khi được yêu cầu triển khai theo tài liệu này, bắt đầu ở Bước 0. Báo điểm tích hợp thực tế, rồi làm Bước 1 và các bước đã được người dùng giao. Không bắt đầu bằng cài Ragas hoặc viết một pipeline mới trước khi có hợp đồng dữ liệu và biết service cần gọi.
