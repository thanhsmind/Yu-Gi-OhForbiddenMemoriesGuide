# Area: Trang hướng dẫn Yu-Gi-Oh! Forbidden Memories

Một trang tra cứu và hướng dẫn chơi, đọc được offline hoàn toàn, không cần
máy chủ và không gọi mạng khi xem.

## Mục đích

Người chơi mở trang lên để trả lời bốn loại câu hỏi:

1. Lá bài này là gì — số thứ tự, chỉ số, hệ, cách lấy, mặt bài trông ra sao.
2. Chơi thế nào — luật cơ bản, Type, Guardian Star, môi trường, Ritual, farm.
3. Ghép bài — lá này ghép ra từ đâu, ghép với gì ra gì.
4. Dữ liệu tới đâu — chỗ nào đã đủ, chỗ nào còn thiếu.

## Bốn khu vực của trang

| Khu vực | Trả lời câu hỏi | Nội dung |
|---|---|---|
| Tra cứu bài | "Lá này là gì" | Danh sách toàn bộ 722 lá, lọc và tìm được, mở ra bảng chi tiết một lá |
| Hướng dẫn | "Chơi thế nào" | Chín mục nội dung, có mục lục nhảy được |
| Fusion | "Ghép thế nào" | Tra cứu hai chiều theo tên lá, cộng ba bảng công thức |
| Độ phủ dữ liệu | "Dữ liệu tới đâu" | Số đếm thật của từng loại dữ liệu, và danh sách thứ chưa có |

## Tra cứu bài

Bảng liệt kê mọi lá bài. Người dùng lọc bằng:

- gõ tên hoặc gõ số thứ tự vào một ô tìm kiếm chung,
- chọn loại lá (quái vật, phép, bẫy, trang bị, nghi lễ),
- chọn Type quái vật,
- bật tùy chọn chỉ hiện lá có chỉ số.

Kết quả hiện theo trang, kèm số lượng khớp trên tổng số. Chọn một dòng thì mở
bảng chi tiết của lá đó: ảnh mặt bài, số thứ tự, tên, loại lá, Type, cấp độ,
ATK, DEF, cặp Guardian Star, mã password, giá StarChip, cách lấy được lá,
tên tiếng Nhật, lore, danh sách trang bị dùng được cho lá đó, và các công thức
fusion liên quan.

Lore có hai bản: bản dịch tiếng Việt (nếu có) hiện làm nội dung chính, và
ngay dưới nó luôn hiện nguyên văn tiếng Anh kèm nhãn "Nguyên văn" ở cỡ chữ
nhỏ hơn, màu nhạt hơn — bản dịch là sản phẩm phái sinh, không bao giờ thay
thế hay che nguyên văn. Lá chưa có bản dịch chỉ hiện nguyên văn tiếng Anh,
không có ô trống.

**Quy tắc trung thực khi hiển thị** (ràng buộc trung tâm của cả khu vực):

- Trường không có dữ liệu hiện chữ "chưa có dữ liệu". Không bao giờ hiện `0`,
  ô trống, hay dấu gạch — ba thứ đó đọc như một giá trị thật.
- Một chỉ số bằng 0 có thật (ví dụ lá phòng thủ 0 ATK) vẫn hiện `0`. Chỉ giá
  trị thiếu mới đổi thành chữ.
- Giá StarChip có một giá trị canh gác nghĩa là "không mua được"; trường này
  hiện "không mua được" chứ không hiện con số canh gác.
- Ảnh thiếu thì hiện ô giữ chỗ ghi rõ tên file cần đặt vào, ở dạng chọn-copy
  được, để người dùng biết phải đặt tên ảnh thế nào.

## Hướng dẫn

Chín mục, theo thứ tự: luật cơ bản và diễn biến một ván; danh sách Type quái
vật; Guardian Star kèm một biểu đồ vòng và luật cộng 500 ATK khi sao khắc;
môi trường (field magic); Ritual; bộ bài khởi đầu và mẹo đầu game; farm bài;
bài nên mua bằng StarChip kèm bảng password; xếp hạng Pow/Tec và cách đánh để
ra drop mong muốn.

Nội dung bám nguồn: không nêu luật hay con số mà nguồn không có. Chỗ nguồn
không đủ dữ liệu thì nói thẳng ra là không đủ — cụ thể, bảng khắc đầy đủ giữa
10 Guardian Star và bảng công thức Ritual đều chưa có, và trang nói vậy thay
vì suy ra.

Tên lá bài xuất hiện trong nội dung hướng dẫn là liên kết nhảy sang bảng chi
tiết của lá đó, khi lá đó có thật.

## Fusion

Tra cứu hai chiều: gõ tên một lá, trang trả về hai danh sách — "ghép ra lá này
bằng gì" và "lá này ghép với gì ra gì". Cả hai chiều tìm theo cả tên lá cụ thể
lẫn hệ fusion mà lá đó thuộc về.

Ba bảng công thức, phản ánh ba cách nguồn mô tả việc ghép bài:

| Bảng | Dạng công thức |
|---|---|
| Cơ bản | hệ + hệ ra một lá; lọc được theo hệ |
| Chính xác | tên lá + tên lá ra một lá |
| Xung đột | khi một lá thuộc hai hệ, cột trái ghép với cột phải cho ra kết quả ưu tiên thay vì kết quả chung |

**Quy tắc tên trong công thức:** một tên khớp được lá có thật thì thành liên
kết sang bảng chi tiết. Tên không khớp hiện dạng chữ thường, không liên kết,
và không sinh ra dòng mới trong bảng tra cứu. Việc khớp tên chấp nhận một bảng
tên đồng nghĩa, vì nguồn công thức và nguồn dữ liệu bài viết tên khác nhau ở
một số lá.

## Độ phủ dữ liệu

Liệt kê số đếm thật của dữ liệu đang nhúng trong trang — tổng số lá, số lá có
chỉ số, số lá có Type, số lá có danh sách trang bị, số công thức mỗi loại, số
lá đã có lore tiếng Việt trên tổng số — và nói rõ những thứ dự án KHÔNG có:
bảng công thức Ritual, bảng drop theo đối thủ, danh sách password đầy đủ.

Dòng số lá đã có lore tiếng Việt ghi rõ đây là **bản dịch máy**, không phải
trích từ nguồn tiếng Việt nào.

Các con số này phải đọc từ dữ liệu tại lúc hiển thị. Gõ cứng con số vào nội
dung là vi phạm: khi dữ liệu đổi mà con số không đổi thì trang nói dối.

## Địa chỉ và lịch sử duyệt

Mọi trạng thái xem được đều có địa chỉ riêng nằm trong phần hash của URL: tab
đang mở, và ở tab tra cứu bài là từ khóa, bộ lọc loại lá, bộ lọc Type, tùy chọn
chỉ hiện lá có chỉ số, số trang, lá đang mở chi tiết; ở tab Fusion là từ khóa
tra cứu và bộ lọc hệ.

Hệ quả bắt buộc:

- Nút Back của trình duyệt đưa người dùng về đúng trạng thái trước đó, kể cả
  trạng thái bộ lọc trung gian — không phải nhảy thẳng về trạng thái rỗng.
  Forward đi tới lại.
- Dán một địa chỉ vào tab mới dựng lại đúng trạng thái đó, kể cả lá đang mở.
- Gõ một chuỗi ký tự vào ô tìm kiếm chỉ tạo **một** mục lịch sử, và Back từ đó
  quay về trạng thái trước khi bắt đầu gõ — kể cả khi chuỗi gõ bắt đầu hoặc kết
  thúc bằng khoảng trắng.
- Địa chỉ hỏng hoặc không hiểu được (mục lục không tồn tại, số trang vượt giới
  hạn, lá không có thật, ký tự thoát sai) không được ném lỗi và không được làm
  trắng trang; nó rơi về một trạng thái hợp lệ và địa chỉ tự chuẩn hóa lại.
- Các liên kết mục lục sẵn có trong mục Hướng dẫn tiếp tục chạy như liên kết
  neo bình thường, không bị định tuyến chiếm.

Chỉ phần hash được đổi, không bao giờ đổi đường dẫn — vì đổi đường dẫn sẽ làm
trang vỡ khi mở bằng cách nhấp đúp vào file. Nếu trình duyệt từ chối luôn cả việc
ghi lịch sử (một số môi trường chặn khi mở từ file), định tuyến rơi về cách gán
hash trực tiếp: mất khả năng gộp mục lịch sử khi gõ, nhưng không mất chức năng
nào và không ném lỗi.

## Nguồn dữ liệu và ranh giới

Ba nguồn, chia việc rõ ràng:

| Nguồn | Cung cấp |
|---|---|
| Bộ dữ liệu bài (722 lá, lấy từ bách khoa Yu-Gi-Oh) | Xương sống bảng tra cứu: số thứ tự, tên, loại lá, Type, cấp độ, ATK, DEF, Guardian Star, password, giá StarChip, lore (nguyên văn tiếng Anh), tên tiếng Nhật, cách lấy, và ảnh mặt bài |
| Ba tài liệu hướng dẫn tiếng Việt | Công thức fusion, danh sách trang bị theo từng lá, và toàn bộ nội dung mục Hướng dẫn |
| Bốn file lore dịch máy (`data/lore-vi/`, khóa theo số thứ tự lá) | Bản dịch tiếng Việt của trường lore, ghép thêm bên cạnh nguyên văn — lá nào chưa có bản dịch giữ `null`, không phải chuỗi rỗng |

Dữ liệu từ tài liệu hướng dẫn được ghép LÊN xương sống theo tên lá, không tạo
dòng mới. Một tên trong tài liệu không khớp lá nào thì giữ nguyên dạng tên, không
biến thành một lá.

## Cách dữ liệu vào trang

Trang tự chứa dữ liệu: toàn bộ dữ liệu nằm ngay trong trang, giữa hai dấu mốc
đóng-mở. Một công cụ sinh dữ liệu đọc hai nguồn trên rồi ghi đè đúng vùng giữa
hai dấu mốc, giữ nguyên phần còn lại. Chạy công cụ đó hai lần liên tiếp phải
cho ra kết quả giống hệt nhau đến từng byte.

Lý do trang không tải dữ liệu từ file rời: trang phải mở được bằng cách nhấp
đúp vào file, và ở chế độ đó trình duyệt chặn việc đọc file ngoài.

Công cụ sinh dữ liệu là phụ thuộc của người phát triển, không phải của người
đọc trang. Người đọc chỉ cần trang và thư mục ảnh.

## Ràng buộc bất biến

Những điều này được kiểm tra tự động và phải luôn đúng:

- Trang không tham chiếu bất kỳ địa chỉ mạng nào, không nạp mã hay phông chữ
  từ bên ngoài, không gọi mạng lúc chạy.
- Mỗi lá có đúng một khóa ảnh; không hai lá nào trùng khóa; khóa chỉ gồm chữ
  thường, chữ số và dấu gạch ngang.
- Mọi lá đều có ảnh tương ứng trong thư mục ảnh.
- Trường thiếu dữ liệu lưu dạng rỗng thật sự, không phải `0` và không phải
  chuỗi trống.
- Mọi con số hiển thị ở khu vực Độ phủ dữ liệu khớp với số đếm lại từ dữ liệu.
- Cả ba bảng công thức phủ **hết** nguồn, đếm lại từ chính file nguồn chứ không
  gõ cứng: số công thức mỗi bảng bằng số dòng tương ứng trong tài liệu, và bộ ba
  (vế trái, vế phải, kết quả) của bảng xung đột khớp nguồn theo đúng bội số —
  một công thức lặp lại nhiều lần trong nguồn phải xuất hiện đúng số lần đó.
- Mọi tên trong bảng tên đồng nghĩa trỏ tới đúng một lá có thật.
- Chạy lại công cụ sinh dữ liệu cho kết quả không đổi.
- Bản dịch tiếng Việt của lore luôn hiển thị kèm nguyên văn tiếng Anh có
  nhãn, không bao giờ giấu nguyên văn; không có bản dịch nào là chuỗi rỗng
  hoặc y hệt nguyên văn tiếng Anh.

## Open Gaps

- Bảng công thức Ritual (triệu hồi hiến tế) chưa có nguồn nào trong dự án.
- Bảng khắc đầy đủ giữa 10 Guardian Star: nguồn chỉ cho một ví dụ cặp.
- Bảng drop bài theo từng đối thủ: chưa có nguồn.
- Danh sách password đầy đủ: nguồn chỉ có khoảng 13 dòng.
- 11 trong 37 nhóm hệ fusion không có danh sách thành viên trong nguồn, nên
  không suy ra được lá nào thuộc nhóm đó.

## Pointers

- `index.html` — cả trang, dữ liệu nhúng giữa `/* FM_DATA:BEGIN */` và
  `/* FM_DATA:END */`.
- `tools/extract_cards.py` — công cụ sinh dữ liệu; `--inject` ghi vào trang.
- `tools/check.py` — bộ kiểm tra các ràng buộc bất biến ở trên (`commands.test`).
- `data/cards.json` — bộ dữ liệu 722 lá; `scripts/fetch_yugipedia_cards.py` tải lại.
- `images/cards/<slug>.png` — 722 ảnh mặt bài.
- `docs/guide/*.md` — ba tài liệu hướng dẫn tiếng Việt.
- Quyết định nền: `docs/history/fm-guide-site/CONTEXT.md` (D1–D7).
