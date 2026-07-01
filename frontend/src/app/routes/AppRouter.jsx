import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import AuthGuard from './AuthGuard';
import ROUTES from './paths';
import MainLayout from '@/shared/layout/MainLayout';
import AuthLayout from '@/shared/layout/AuthLayout';
import { SpinnerCenter } from '@/shared/ui';

import LoginPage from '@/features/auth/pages/LoginPage';
import RegisterPage from '@/features/auth/pages/RegisterPage';

const DashboardPage = lazy(() => import('@/features/dashboard/pages/DashboardPage'));
const TransactionsPage = lazy(() => import('@/features/transactions/pages/TransactionsPage'));
const BudgetsPage = lazy(() => import('@/features/budgets/pages/BudgetsPage'));
const CategoriesPage = lazy(() => import('@/features/categories/pages/CategoriesPage'));

const Guarded = ({ children }) => (
  <AuthGuard requireAuth>
    <MainLayout>
      <Suspense fallback={<SpinnerCenter />}>{children}</Suspense>
    </MainLayout>
  </AuthGuard>
);

const AuthRoute = ({ children }) => (
  <AuthGuard requireAuth={false} redirectIfAuthenticated>
    <AuthLayout>{children}</AuthLayout>
  </AuthGuard>
);

const AppRouter = () => (
  <Routes>
    <Route path={ROUTES.HOME} element={<Navigate to={ROUTES.DASHBOARD} replace />} />
    <Route path={ROUTES.LOGIN} element={<AuthRoute><LoginPage /></AuthRoute>} />
    <Route path={ROUTES.REGISTER} element={<AuthRoute><RegisterPage /></AuthRoute>} />

    <Route path={ROUTES.DASHBOARD} element={<Guarded><DashboardPage /></Guarded>} />
    <Route path={ROUTES.TRANSACTIONS} element={<Guarded><TransactionsPage /></Guarded>} />
    <Route path={ROUTES.BUDGETS} element={<Guarded><BudgetsPage /></Guarded>} />
    <Route path={ROUTES.CATEGORIES} element={<Guarded><CategoriesPage /></Guarded>} />

    <Route path="*" element={<Navigate to={ROUTES.DASHBOARD} replace />} />
  </Routes>
);

export default AppRouter;
