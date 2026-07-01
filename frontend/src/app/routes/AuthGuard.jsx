import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import ROUTES from './paths';

const AuthGuard = ({ children, requireAuth = true, redirectIfAuthenticated = false }) => {
  const { isAuthenticated } = useAuth();
  const hasToken = Boolean(localStorage.getItem('auth_token'));
  const canAccess = isAuthenticated && hasToken;

  if (requireAuth && !canAccess) return <Navigate to={ROUTES.LOGIN} replace />;
  if (!requireAuth && redirectIfAuthenticated && canAccess)
    return <Navigate to={ROUTES.DASHBOARD} replace />;

  return children;
};

export default AuthGuard;
