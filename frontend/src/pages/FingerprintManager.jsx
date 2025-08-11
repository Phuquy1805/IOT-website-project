import React, { useState, useEffect, useCallback } from 'react';
import { getFingerprints, registerFingerprint, deleteFingerprint } from '../services/api';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

export default function FingerprintManager() {
  const [fingerprints, setFingerprints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRegistering, setIsRegistering] = useState(false);

  const fetchFingerprints = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getFingerprints();
      setFingerprints(res.data);
    } catch (error) {
      toast.error("Failed to load fingerprints.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFingerprints();
  }, [fetchFingerprints]);

  const handleRegister = async () => {
    setIsRegistering(true);
    toast.info("Gửi yêu cầu đến thiết bị... Vui lòng làm theo hướng dẫn trên LCD.", { autoClose: 15000 });
    try {
      await registerFingerprint();
      // Sau một khoảng thời gian, fetch lại danh sách để cập nhật
      setTimeout(fetchFingerprints, 20000); // Đợi thiết bị xử lý xong
    } catch (error) {
      toast.error("Gửi yêu cầu đăng ký thất bại.");
    } finally {
      setTimeout(() => setIsRegistering(false), 20000);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm(`Bạn có chắc muốn xóa vân tay ID #${id}?`)) {
      try {
        toast.info(`Đang gửi yêu cầu xóa vân tay #${id}...`);
        await deleteFingerprint(id);
        // Cập nhật UI ngay lập tức để có trải nghiệm tốt hơn
        setFingerprints(prev => prev.filter(fp => fp.id !== id));
        toast.success(`Đã gửi lệnh xóa vân tay #${id} thành công!`);
      } catch (error) {
        toast.error(`Gửi yêu cầu xóa thất bại cho vân tay #${id}.`);
      }
    }
  };

  return (
    <div className="container py-4">
      <ToastContainer position="top-right" />
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h3>Quản lý vân tay</h3>
        <button
          className="btn btn-primary"
          onClick={handleRegister}
          disabled={isRegistering}
        >
          {isRegistering ? 'Đang chờ thiết bị...' : 'Đăng ký vân tay mới'}
        </button>
      </div>
      
      <div className="card">
        <div className="card-body">
          <table className="table table-hover">
            <thead>
              <tr>
                <th scope="col">Fingerprint ID</th>
                <th scope="col">Tên người dùng</th>
                <th scope="col">Tên gợi nhớ</th>
                <th scope="col">Ngày đăng ký</th>
                <th scope="col">Hành động</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="5" className="text-center">Loading...</td></tr>
              ) : (
                fingerprints.map(fp => (
                  <tr key={fp.id}>
                    <th scope="row">{fp.id}</th>
                    <td>{fp.username}</td>
                    <td>{fp.name}</td>
                    <td>{new Date(fp.created_at * 1000).toLocaleString()}</td>
                    <td>
                      <button 
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDelete(fp.id)}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))
              )}
              {!loading && fingerprints.length === 0 && (
                <tr><td colSpan="5" className="text-center text-muted">Chưa có vân tay nào được đăng ký.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}