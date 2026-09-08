import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import { PermissionRoute } from './auth/PermissionRoute'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { Layout } from './components/Layout'
import { AgentDetailPage } from './pages/AgentDetailPage'
import { AgentsPage } from './pages/AgentsPage'
import { AlertsPage } from './pages/AlertsPage'
import { AlertRulesPage } from './pages/AlertRulesPage'
import { DashboardOverviewPage } from './pages/DashboardOverviewPage'
import { GroupDetailPage } from './pages/GroupDetailPage'
import { GroupsPage } from './pages/GroupsPage'
import { InfrastructurePage } from './pages/InfrastructurePage'
import { PhotoServicesPage } from './pages/PhotoServicesPage'
import { BackupPage } from './pages/BackupPage'
import { LoginPage } from './pages/LoginPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { SettingsPage } from './pages/SettingsPage'
import { UsersPage } from './pages/UsersPage'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route index element={<Navigate replace to="/dashboard" />} />
              <Route path="dashboard" element={<DashboardOverviewPage />} />
              <Route path="agents" element={<AgentsPage />} />
              <Route path="agents/:id" element={<AgentDetailPage />} />
              <Route element={<PermissionRoute permission="groups" />}>
                <Route path="groups" element={<GroupsPage />} />
                <Route path="groups/:groupId" element={<GroupDetailPage />} />
              </Route>
              <Route element={<PermissionRoute permission="infrastructure" />}>
                <Route path="infrastructure" element={<InfrastructurePage />} />
              </Route>
              <Route element={<PermissionRoute permission="photo_services" />}>
                <Route path="photo-services" element={<PhotoServicesPage />} />
              </Route>
              <Route element={<PermissionRoute permission="backup" />}>
                <Route path="backup" element={<BackupPage />} />
              </Route>
              <Route path="alerts" element={<AlertsPage />} />
              <Route element={<PermissionRoute permission="alert_rules" />}>
                <Route path="alert-rules" element={<AlertRulesPage />} />
              </Route>
              <Route element={<PermissionRoute permission="notifications" />}>
                <Route path="notifications" element={<NotificationsPage />} />
              </Route>
              <Route element={<PermissionRoute permission="users" />}>
                <Route path="users" element={<UsersPage />} />
              </Route>
              <Route element={<PermissionRoute permission="settings" />}>
                <Route path="settings" element={<SettingsPage />} />
              </Route>
              <Route path="*" element={<Navigate replace to="/dashboard" />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
