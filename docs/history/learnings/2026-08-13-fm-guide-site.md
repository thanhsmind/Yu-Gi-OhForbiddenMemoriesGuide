# Learnings — fm-guide-site (2026-08-13)

Feature: trang hướng dẫn Yu-Gi-Oh! Forbidden Memories, 5 cell, judge PASS.

## 1. Đo nguồn trước khi hứa phạm vi — và đo lại con số của chính mình

Yêu cầu ban đầu nói "720 quân bài, mỗi lá có ATK/DEF/hệ". Repo lúc đó chỉ có ba
file markdown. Một lần quét thật cho thấy: 653 lá có số+tên, 101 lá có ATK/DEF,
0 lá có Type. Nếu không đo mà cứ dựng, kết quả sẽ là một bảng 85% ô rỗng — hoặc
tệ hơn, 720 dòng số liệu bịa từ trí nhớ.

Nhưng bản nháp kế hoạch đầu tiên tự bịa ra ba con số sai (261 tên roster, 37
nhóm có danh sách, 478 công thức) vì script đo của chính nó có lỗi tách cột. Một
vòng soi độc lập chạy lại từng lệnh đếm bắt được cả ba, và bắt luôn một hệ thống
"khớp tên theo tiền tố" được thiết kế chỉ để vá cho giả định cột-rộng-28 vốn sai.
Sửa giả định thì cả hệ thống đó biến mất, thay bằng một regex và ba dòng alias.

**Rút ra:** con số trong Discovery là *bằng chứng*, phải chạy lại được. Một vòng
soi độc lập trước gate, có yêu cầu "đừng tin số của tôi, chạy lại", rẻ hơn nhiều
so với việc phát hiện sau khi đã code. Và khi một subsystem sinh ra chỉ để vá một
giả định, hãy kiểm tra giả định trước khi xây subsystem.

## 2. Ranh giới "không bịa" phải sống ở tầng kiểm tra, không phải ở tầng lời hứa

D4 nói "ô không có nguồn để rỗng, không hiện 0". Điều đó tự nó không giữ được gì.
Cái giữ được là các khẳng định chạy mỗi lần cap cell: không lá nào nửa-rỗng
nửa-0; mọi số trên tab độ phủ khớp số đếm lại; mọi khóa alias trỏ tới đúng một lá
có thật. Judge chứng minh chúng thật sự đỏ được bằng cách phá từng cái trên một
bản sao cách ly.

Judge cũng bắt được một thứ lời hứa không phủ: giá StarChip có giá trị canh gác
`999999` nghĩa là "không mua được", và trang in nó ra như một cái giá thật. Không
ai bịa gì cả — dữ liệu nguồn ghi vậy — nhưng người đọc vẫn bị nói dối.

**Rút ra:** với ràng buộc kiểu "không được nói dối người đọc", hãy hỏi thêm câu
"giá trị nào *đọc như* thật mà không phải thật" — sentinel, giá trị mặc định,
chuỗi giữ chỗ — chứ không chỉ hỏi "ô nào rỗng".

## 3. Một trang "thuần HTML" mà có 700 dòng dữ liệu vẫn cần bước sinh

Ràng buộc "một file, nhấp đúp là chạy" loại `fetch()` (trình duyệt chặn trên
`file://`) và loại luôn file dữ liệu rời. Nhưng gõ tay 653 dòng thì vi phạm ranh
giới không-bịa. Lối ra: giữ trang là một file tự chứa, nhưng dữ liệu nằm giữa hai
dấu mốc và một công cụ ghi đè đúng vùng đó.

Điều đáng ghi là cách xử lý mâu thuẫn: "không build step" và "không gõ tay số
liệu" không thể cùng đúng tuyệt đối. Thay vì tự diễn giải lại một trong hai,
mâu thuẫn được nêu thẳng cho người dùng ở gate, và câu trả lời thành một quyết
định có ghi (D6): trang zero-dependency cho người đọc, Python cho người phát
triển.

**Rút ra:** khi hai quyết định đã khóa va nhau, đó là câu hỏi cho người dùng, không
phải chỗ để agent chọn bên rồi khai là "vẫn thỏa cả hai".

## 4. Hai session cùng repo: phát hiện được là nhờ worker, không nhờ khóa

Một session thứ hai đang song song kéo bộ dữ liệu 722 lá từ Yugipedia — đầy đủ
hơn hẳn kết quả mining — và đã ghi decision đánh dấu là người dùng duyệt.
Session này không hề biết cho tới khi một worker báo lại vì thấy file lạ trong
cây làm việc. Trước đó chỉ mục git đã bị rối một lần do hai bên cùng `git add`.

Cái cứu tình huống: worker **không** tự diễn giải lại quyết định đã khóa để chạy
theo hướng mới, mà build đúng theo CONTEXT.md rồi báo lên. Nếu nó "tự hiểu" thì
sản phẩm sẽ nằm giữa hai nguồn, không nguồn nào đầy đủ.

**Rút ra:** trước khi vào việc trên một repo dùng chung, kiểm tra session đang
sống. Và khi worker gặp bằng chứng mâu thuẫn với quyết định đã khóa, báo lên là
đúng — tự chọn bên là lỗi.

## 5. Ba con số dừng cuộc phỏng vấn

Câu hỏi mở với người dùng gói gọn thành ba lựa chọn (nguồn dữ liệu, cấu trúc
trang, cách đặt tên ảnh) hỏi một lần, kèm bảng so sánh độ phủ thật khi cần họ
quyết. Người dùng trả lời bằng ba lần "ok" ngắn và một câu chỉ đạo. Bảng so sánh
653-lá-98-chỉ-số với 722-lá-621-chỉ-số làm cho quyết định đổi nguồn hiển nhiên
trong một dòng, không cần tranh luận.

**Rút ra:** khi cần người dùng quyết giữa hai đường, đưa số đo cạnh nhau thay vì
mô tả bằng lời. Quyết định tự lộ ra.
