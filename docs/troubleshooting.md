# Troubleshooting – lỗi đã gặp và cách xử lý

Các mục dưới đây được ghi lại từ lần chạy thành công trong môi trường cụ thể:
Windows + SOLIDWORKS 2026 (Type Library 22.0) + Python 3.14 64-bit + pywin32.

## 1. MakePy / COM wrapper

**Triệu chứng:** `EnsureDispatch` báo không thể tự động chạy MakePy.

**Cách đã làm:** chạy:

```powershell
python -m win32com.client.makepy
```

Chọn **SOLIDWORKS 2026 Type Library (22.0)**.

Sau đó kết nối bằng:

```python
sw = win32com.client.Dispatch("SldWorks.Application")
```

## 2. Lấy template Part

**Cách đã chạy thành công:**

```python
template = sw.GetDocumentTemplate(1, "", 0, 0.0, 0.0)
model = sw.NewDocument(template, 0, 0.0, 0.0)
```

Trong trường hợp này, `1` là `swDocPART`.

Kiểm tra template khác `None` và đường dẫn tồn tại trước khi gọi `NewDocument`.

## 3. `SelectByID2` báo COM Type mismatch

**Triệu chứng:** `com_error(-2147352571, 'Type mismatch.', None, 8)` khi chọn Front Plane hoặc Sketch.

**Cách đã chạy thành công trong dự án:**

```python
plane = model.FeatureByName("Front Plane")
plane.Select2(False, 0)

sketch = model.FeatureByName("Sketch1")
sketch.Select2(False, 0)
```

Tránh dùng lại lời gọi `SelectByID2(..., None, ...)` trong đúng môi trường này khi chưa xác minh kiểu COM của tham số Callout.

## 4. `EditRebuild3()` báo `'bool' object is not callable`

**Triệu chứng:**

```text
TypeError: 'bool' object is not callable
```

Traceback trỏ tới `model.EditRebuild3()`.

**Cách đã chạy thành công:**

```python
rebuild_result = model.ForceRebuild3(False)
```

Lưu ý: đây là kết quả kiểm chứng của wrapper/môi trường hiện tại, không phải khẳng định mọi COM wrapper đều ánh xạ giống nhau.

## 5. Lưu file thất bại

Dùng:

```python
save_result = model.SaveAs3(PART_PATH, 0, 1)
```

Nếu kết quả false, lấy chẩn đoán:

```python
print(model.GetSaveError())
print(model.GetSaveWarning())
```

Sau khi lưu, kiểm tra thêm `os.path.isfile(PART_PATH)`.

## 6. Quy tắc xử lý lỗi lần sau

1. Không sửa nhiều bước cùng lúc.
2. Giữ lại bước đã chạy thành công.
3. In log trước và sau mỗi lời gọi COM quan trọng.
4. Lấy traceback đầy đủ bằng `traceback.print_exc()`.
5. Ghi lại phiên bản SOLIDWORKS, Python và pywin32 khi lỗi khác môi trường.
6. Đối chiếu API Help của đúng phiên bản trước khi đổi chữ ký hàm hoặc tham số.
