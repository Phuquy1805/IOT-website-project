import React, { useState, useEffect, useCallback } from 'react';
import { getFingerprints, registerFingerprint, deleteFingerprint } from '../services/api';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const UPDATE_DELAY_MS = 5000; // 5 giây là một khoảng thời gian hợp lý

export default function FingerprintManager() {
  const [fingerprints, setFingerprints] = useState([]);
  const [count, setCount] = useState(0);
  const [capacity, setCapacity] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);

  const fetchFingerprints = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getFingerprints();
      setFingerprints(res.data.items);
      setCount(res.data.count);
      setCapacity(res.data.capacity);
    } catch (error) {
      toast.error("Failed to load fingerprints.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFingerprints();
  }, [fetchFingerprints]);

  const scheduleUpdate = (actionType) => {
    toast.info(`Thao tác ${actionType} đã được gửi. Đang chờ thiết bị xử lý...`);
    
    setTimeout(() => {
      toast.info("Đang cập nhật lại danh sách...");
      fetchFingerprints();
      setIsProcessing(false); 
    }, UPDATE_DELAY_MS);
  };

  const handleRegister = async () => {
    if (capacity > 0 && count >= capacity) {
      toast.warn("Bộ nhớ vân tay đã đầy!");
      return;
    }
    
    setIsProcessing(true); // Vô hiệu hóa tất cả các nút
    
    try {
      await registerFingerprint();
      scheduleUpdate('đăng ký'); // Lên lịch cập nhật
    } catch (error) {
      if (error.response && error.response.status === 409) {
        toast.error("Gửi yêu cầu thất bại: Bộ nhớ đã đầy.");
      } else {
        toast.error("Gửi yêu cầu đăng ký thất bại.");
      }
      setIsProcessing(false); // Bật lại nút nếu có lỗi ngay lập tức
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm(`Bạn có chắc muốn xóa vân tay ID #${id}?`)) {
      setIsProcessing(true); // Vô hiệu hóa tất cả các nút
      
      try {
        await deleteFingerprint(id);
        scheduleUpdate('xóa'); // Lên lịch cập nhật
      } catch (error) {
        toast.error(`Gửi yêu cầu xóa thất bại cho vân tay #${id}.`);
        setIsProcessing(false); // Bật lại nút nếu có lỗi ngay lập tức
      }
    }
  };

  const isFull = capacity > 0 && count >= capacity;

  return (
    <div className="container py-4">
      <ToastContainer position="top-right" autoClose={5000} hideProgressBar={false} />
      
      {/* Header and Controls */}
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h3>Quản lý vân tay</h3>
        <div className="d-flex align-items-center gap-3">
          <span className={`fw-bold ${isFull ? 'text-danger' : 'text-muted'}`}>
            Đã dùng: {count} / {capacity}
          </span>
          <button
            className="btn btn-primary"
            onClick={handleRegister}
            disabled={isRegistering || isFull}
          >
            {isRegistering ? 'Đang chờ thiết bị...' : 'Đăng ký vân tay mới'}
          </button>
        </div>
      </div>
      
      {/* Warning message when full */}
      {isFull && (
        <div className="alert alert-warning" role="alert">
          Bộ nhớ cảm biến vân tay đã đầy. Vui lòng xóa bớt vân tay cũ trước khi đăng ký mới.
        </div>
      )}
      
      {/* Fingerprints Table */}
      <div className="card">
        <div className="card-body">
          <table className="table table-hover align-middle">
            <thead>
              <tr>
                <th scope="col">ID</th>
                <th scope="col">Người dùng</th>
                <th scope="col">Tên gợi nhớ</th>
                <th scope="col">Ngày đăng ký</th>
                <th scope="col" className="text-end">Hành động</th>
              </tr>
            </thead>
            <tbody>
              {loading && !isProcessing ? (
                <tr><td colSpan="5" className="text-center p-5"><div className="spinner-border" role="status"><span className="visually-hidden">Loading...</span></div></td></tr>
              ) : fingerprints.length > 0 ? (
                fingerprints.map(fp => (
                  <tr key={fp.id}>
                    <th scope="row">{fp.id}</th>
                    <td>{fp.username}</td>
                    <td>{fp.name}</td>
                    <td>{new Date(fp.created_at * 1000).toLocaleString()}</td>
                    <td className="text-end">
                      <button 
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDelete(fp.id)}
                        disabled={isProcessing}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan="5" className="text-center text-muted p-4">Chưa có vân tay nào được đăng ký.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}