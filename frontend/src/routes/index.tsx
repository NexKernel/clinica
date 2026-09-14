import { Navigate, Route, Routes } from 'react-router-dom'

import { AppLayout } from '@/layouts/AppLayout'
import { AppointmentsPage } from '@/pages/AppointmentsPage'
import { BillingPage } from '@/pages/BillingPage'
import { ComingSoonPage } from '@/pages/ComingSoonPage'
import { ConsultationsPage } from '@/pages/ConsultationsPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { LoginPage } from '@/pages/LoginPage'
import { MedicalRecordsPage } from '@/pages/MedicalRecordsPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { PatientDetailPage } from '@/pages/PatientDetailPage'
import { PatientsPage } from '@/pages/PatientsPage'
import { PharmacyPage } from '@/pages/PharmacyPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { PurchasesPage } from '@/pages/PurchasesPage'
import { RemindersPage } from '@/pages/RemindersPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { SharedResultPage } from '@/pages/SharedResultPage'
import { StudiesPage } from '@/pages/StudiesPage'
import { UsersPage } from '@/pages/UsersPage'
import { NAV_ITEMS, rolesForNavItem } from '@/routes/navigation'
import { ProtectedRoute, PublicOnlyRoute } from '@/routes/ProtectedRoute'
import { ROUTES, SHARED_RESULT_PATH } from '@/routes/paths'

/** Módulos aún no implementados: se registran desde la navegación centralizada. */
const PENDING_MODULES = NAV_ITEMS.filter((item) => item.comingSoon)

/** Cada módulo conserva los roles declarados en la navegación. */
const rolesFor = rolesForNavItem

export function AppRoutes() {
  return (
    <Routes>
      {/* Consulta de resultados por enlace: pública y sin sesión iniciada. */}
      <Route path={SHARED_RESULT_PATH} element={<SharedResultPage />} />

      <Route element={<PublicOnlyRoute />}>
        <Route path={ROUTES.login} element={<LoginPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path={ROUTES.dashboard} element={<DashboardPage />} />
          <Route path={ROUTES.profile} element={<ProfilePage />} />

          <Route element={<ProtectedRoute roles={rolesFor('patients')} />}>
            <Route path={ROUTES.patients} element={<PatientsPage />} />
            <Route path={ROUTES.patientDetail} element={<PatientDetailPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={rolesFor('appointments')} />}>
            <Route path={ROUTES.appointments} element={<AppointmentsPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={rolesFor('consultations')} />}>
            <Route path={ROUTES.consultations} element={<ConsultationsPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={rolesFor('medical-records')} />}>
            <Route path={ROUTES.medicalRecords} element={<MedicalRecordsPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={rolesFor('studies')} />}>
            <Route path={ROUTES.studies} element={<StudiesPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={rolesFor('documents')} />}>
            <Route path={ROUTES.documents} element={<DocumentsPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={rolesFor('reminders')} />}>
            <Route path={ROUTES.reminders} element={<RemindersPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={rolesFor('billing')} />}>
            <Route path={ROUTES.billing} element={<BillingPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={rolesFor('pharmacy')} />}>
            <Route path={ROUTES.pharmacy} element={<PharmacyPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={rolesFor('purchases')} />}>
            <Route path={ROUTES.purchases} element={<PurchasesPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={rolesFor('reports')} />}>
            <Route path={ROUTES.reports} element={<ReportsPage />} />
          </Route>

          <Route element={<ProtectedRoute roles={['ADMIN']} />}>
            <Route path={ROUTES.users} element={<UsersPage />} />
            <Route path={ROUTES.settings} element={<SettingsPage />} />
          </Route>

          {PENDING_MODULES.map((item) => (
            <Route key={item.key} element={<ProtectedRoute roles={item.roles} />}>
              <Route path={item.path} element={<ComingSoonPage />} />
            </Route>
          ))}

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to={ROUTES.dashboard} replace />} />
    </Routes>
  )
}
