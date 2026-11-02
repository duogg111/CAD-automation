# Workflow đã chạy thành công

Quy trình tạo khối hộp 100 × 60 × 30 mm:

1. Khởi tạo COM bằng `pythoncom.CoInitialize()`.
2. Kết nối SOLIDWORKS bằng `win32com.client.Dispatch("SldWorks.Application")`.
3. Hiện cửa sổ SOLIDWORKS bằng `sw.Visible = True`.
4. Lấy template Part mặc định bằng `GetDocumentTemplate(1, "", 0, 0.0, 0.0)`.
5. Tạo tài liệu bằng `NewDocument(...)`.
6. Lấy Front Plane qua `FeatureByName("Front Plane")` rồi chọn bằng `Select2(False, 0)`.
7. Bắt đầu Sketch bằng `SketchManager.InsertSketch(True)`.
8. Vẽ hình chữ nhật bằng `CreateCornerRectangle(...)`. Tọa độ API dùng mét.
9. Kết thúc Sketch và lấy `Sketch1` qua `FeatureByName("Sketch1")`.
10. Chọn Sketch bằng `Select2(False, 0)`.
11. Tạo khối bằng `FeatureManager.FeatureExtrusion2(...)`.
12. Hiển thị góc nhìn Trimetric và Zoom to Fit.
13. Rebuild bằng `ForceRebuild3(False)`.
14. Lưu bằng `SaveAs3(...)`, kiểm tra kết quả và xác nhận file tồn tại.

## Quy ước đơn vị

Thông số thiết kế lưu bằng mm để dễ đọc. SOLIDWORKS API nhận tọa độ/độ dài theo mét trong các lệnh được dùng ở script này:

`m = mm / 1000`
