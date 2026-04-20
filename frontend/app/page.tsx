import PumpStatus from "@/components/IrrigationMonitor";
import SensorChart from "@/components/SensorChart";
import PlantLight from "@/components/LightStatus";
import TempHumidityCard from "@/components/GlasshouseCard";
import WeatherCard from "@/components/OutdoorDataCard";
import Image from "next/image";
import GrowthStatus from "@/components/GrowthStatus";
import SoilHumidityScatter from "@/components/SoilHumidityScatter";
import TemperatureComparisonScatter from "@/components/TemperatureComparisonScatter";
import DailyTempHumidityComparisonBarChart from "@/components/DailyTempHumidityComparisonBarChart";
import SoilMoisturePumpChart from "@/components/SoilMoisturePumpChart";
import DataSharingApiCard from "@/components/DataSharingApiCard";

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
        <div className="grid items-stretch gap-4 md:grid-cols-2">
          <div className="h-full">
            <GrowthStatus />
          </div>
          <div className="h-full">
            <PlantLight />
          </div>
        </div>

        <div className="grid items-stretch gap-4 md:grid-cols-[1.35fr_0.85fr_1fr]">
          <PumpStatus />
          <TempHumidityCard />
          <WeatherCard />
        </div>

        <div className="grid items-stretch gap-4 md:grid-cols-1">
          <SensorChart />
        </div>

        <div className="grid items-stretch gap-4 md:grid-cols-1">
          <SoilHumidityScatter />
        </div>

        <div className="grid items-stretch gap-4 md:grid-cols-1">
          <TemperatureComparisonScatter />
        </div>

        <div className="grid items-stretch gap-4 md:grid-cols-1">
          <DailyTempHumidityComparisonBarChart />
        </div>

        <div className="grid items-stretch gap-4 md:grid-cols-1">
          <SoilMoisturePumpChart />
        </div>

        <div className="grid items-stretch gap-4 md:grid-cols-1">
          <DataSharingApiCard />
        </div>
      </main>
    </div>
  );
}
