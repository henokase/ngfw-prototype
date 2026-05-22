import { X } from 'lucide-react'

interface ConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmText?: string
  confirmVariant?: 'danger' | 'warning' | 'primary'
  loading?: boolean
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  confirmVariant = 'primary',
  loading = false,
}) => {
  if (!isOpen) return null

  const variantStyles = {
    danger: 'bg-gradient-to-r from-[#ff3b3b] to-[#cc2f2f] hover:shadow-[0_0_20px_rgba(255,59,59,0.5)]',
    warning: 'bg-gradient-to-r from-[#ff9500] to-[#cc7700] hover:shadow-[0_0_20px_rgba(255,149,0,0.5)]',
    primary: 'bg-gradient-to-r from-[#00f0ff] to-[#00c4cc] hover:shadow-[0_0_20px_rgba(0,240,255,0.5)]',
  }

  return (
    <div 
      className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm animate-fade-in" />
      
      <div className="relative bg-card border border-subtle rounded-xl p-6 w-full max-w-md animate-slide-up shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted hover:text-primary transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
          disabled={loading}
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-start gap-4 mb-6">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
            confirmVariant === 'danger' ? 'bg-danger/10 text-danger' :
            confirmVariant === 'warning' ? 'bg-warning/10 text-warning' :
            'bg-cyan/10 text-cyan'
          }`}>
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-[family-name:var(--font-display)] font-semibold text-primary mb-2">
              {title}
            </h3>
            <p className="text-secondary text-sm leading-relaxed">
              {message}
            </p>
          </div>
        </div>

        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2.5 rounded-lg bg-border-subtle text-secondary hover:bg-card-hover transition-all min-w-[100px] min-h-[44px] font-medium disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`px-4 py-2.5 rounded-lg text-[var(--color-bg-inverse)] font-semibold transition-all min-w-[100px] min-h-[44px] disabled:opacity-50 disabled:cursor-not-allowed ${variantStyles[confirmVariant]}`}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Processing
              </span>
            ) : confirmText}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slide-up {
          from { 
            opacity: 0;
            transform: translateY(20px) scale(0.95);
          }
          to { 
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        .animate-fade-in {
          animation: fade-in 0.2s ease-out forwards;
        }
        .animate-slide-up {
          animation: slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
      `}</style>
    </div>
  )
}

export default ConfirmModal