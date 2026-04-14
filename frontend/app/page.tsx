import HarvestETA from "@/components/HarvestETA";
import ObsForm from "@/components/ObsForm";
import PumpStatus from "@/components/PumpStatus";
import SensorChart from "@/components/SensorChart";
import PlantLight from "@/components/PlantLight";
import WeatherCard from "@/components/WeatherCard";
import Image from "next/image";
import GrowthStatus from "@/components/GrowthStatus";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#F1E4C3] to-white text-slate-900">
      <header className="border-b border-slate-200/70 bg-white backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Image src="/assets/logos/AutoGrow.png" alt="AutoGrow logo" width={180} height={60} priority />
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
        <div className="grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2 h-full">
            <GrowthStatus />
          </div>
          <WeatherCard />
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <PumpStatus />
          <PlantLight />
          <div className="md:col-span-2 lg:col-span-3">
            <SensorChart />
          </div>
        </div>

        <div className="grid gap-4">
          <ObsForm />
        </div>
      </main>
    </div>
  );
}
