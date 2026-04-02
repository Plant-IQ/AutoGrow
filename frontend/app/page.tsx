import HarvestETA from "@/components/HarvestETA";
import HealthGauge from "@/components/HealthGauge";
import ObsForm from "@/components/ObsForm";
import PumpStatus from "@/components/PumpStatus";
import SensorChart from "@/components/SensorChart";
import StageCard from "@/components/StageCard";
import PlantLight from "@/components/PlantLight";
import Image from "next/image";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#F1E4C3] to-white text-slate-900">
      <header className="border-b border-slate-200/70 bg-white backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Image src="/assets/logos/AutoGrow.png" alt="AutoGrow logo" width={150} height={50} priority />
            <div className="h-10 w-px bg-slate-200" />
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Dashboard</p>
              <h1 className="text-2xl font-semibold">Grow room overview</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-full border border-[color:var(--brand-primary)]/30 bg-[color:var(--brand-primary)]/10 px-3 py-1 text-sm font-medium text-[color:var(--brand-primary)]">
              Live mock data
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8">
        <div className="grid gap-4 md:grid-cols-4">
          <StageCard />
          <HarvestETA />
          <PumpStatus />
          <PlantLight />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <HealthGauge />
          <div className="lg:col-span-2">
            <SensorChart />
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <ObsForm />
          <div className="card">
            <p className="label">Notes</p>
            <p className="text-sm text-slate-600">
              Use this panel during class to demo how you collected data. Screen-share or bring your laptop and
              walk through sensor setup, sampling cadence, and any issues you hit so we can troubleshoot together.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
