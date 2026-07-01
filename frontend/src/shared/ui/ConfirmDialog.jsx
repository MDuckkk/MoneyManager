import Modal from './Modal';

const ConfirmDialog = ({
  open,
  title = 'Xác nhận',
  message,
  confirmText = 'Xóa',
  onConfirm,
  onClose,
  loading = false,
}) => (
  <Modal
    open={open}
    title={title}
    onClose={onClose}
    footer={
      <>
        <button className="btn btn-ghost" onClick={onClose} disabled={loading}>
          Hủy
        </button>
        <button className="btn btn-danger" onClick={onConfirm} disabled={loading}>
          {confirmText}
        </button>
      </>
    }
  >
    <p className="muted">{message}</p>
  </Modal>
);

export default ConfirmDialog;
