"use client";
import PatientManagementPanel from "@/components/reception/PatientManagementPanel";

export default function PatientsPage() {
  return (
    <div className="p-4 md:p-6" style={{ minHeight: "calc(100vh - 52px)" }}>
      <div className="h-full" style={{ minHeight: "calc(100vh - 100px)" }}>
        <PatientManagementPanel />
      </div>
    </div>
  );
}
