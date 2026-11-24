/**
 * « Avant le camion » (left column of the Voix page, toggled by the header button or ?camion=1).
 *
 * The morning check of the AI service (GET /ai/outbound/truck-calls, apps/ai/app/services/truck_calls.py): every
 * weighed order of the day, the calls the agent must make before the trucks leave, the gaps left alone and why, and
 * what the calls already settled. Polled every 4 s, so a call ending turns its card to « fait » on its own.
 *
 * « Appeler » starts a fresh session and sends the call's `startWith` (« /appel ord_… ») as a text message on the open
 * voice socket: the agent speaks first, then push-to-talk as usual.
 *
 * The ERP's clock is frozen at 05:00, after every departure. For the story, the panel runs a demo clock that starts
 * at 04:38 when it opens and ticks in real seconds (say so in the demo). Read-only: nothing here writes to the ERP.
 */
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock, Phone, PhoneOutgoing, RotateCcw, Truck } from "lucide-react";
import { AI_BASE } from "@/lib/api";
import { cn } from "@/lib/cn";
import { Badge, Button, ErrorState, Money, SECTION_LABEL, Skeleton } from "@/ui";

interface Problem {
  kind: "missing" | "short" | "over" | "replaced";
  productName: string;
  unit?: string;
  ordered: number;
  onTruck: number;
  amount: number;
  replacedBy?: { productName: string; qty: number; unit?: string };
}
interface TruckCall {
  orderId: string;
  orderNumber?: string;
  clientName: string;
  city?: string;
  contact?: { name?: string; role?: string; phone?: string } | null;
  truck?: { route?: string; driver?: string; departure?: string; eta?: string; stop?: number; stops?: number } | null;
  problems: Problem[];
  substitution: "ok" | "refuse" | "ask";
  substitutionRule?: string;
  status: "to_call" | "done";
  outcome?: { title?: string; description?: string } | null;
  lastAttempt?: string | null;
  recovered?: number;
  startWith: string;
}
interface Tolerated { orderId: string; clientName: string; productName: string; ordered: number; onTruck: number; unit?: string; why: string }
interface TruckBoardData {
  today: string;
  checked: { orders: number; lines: number };
  calls: TruckCall[];
  tolerated: Tolerated[];
  atStake: number;
  recovered: number;
  toCall: number;
}

const fetchBoard = async (): Promise<TruckBoardData> => {
  const res = await fetch(`${AI_BASE}/outbound/truck-calls`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
};

const DEMO_START_S = 4 * 3600 + 38 * 60; // 04:38:00
const KIND_LABEL: Record<Problem["kind"], string> = { missing: "absent du camion", short: "poids court", over: "poids au-dessus", replaced: "remplacé dans le camion" };
const RULE: Record<TruckCall["substitution"], { label: string; tone: "destructive" | "success" | "warning" }> = {
  refuse: { label: "Refuse les substitutions", tone: "destructive" },
  ok: { label: "Accepte si on prévient", tone: "success" },
  ask: { label: "Rien dans sa fiche : demander", tone: "warning" },
};

const fr = (n: number) => String(Math.round(n * 100) / 100).replace(".", ",");
const hhmmss = (s: number) => [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60].map((x) => String(x).padStart(2, "0")).join(":");
const toSeconds = (hhmm?: string) => {
  const [h, m] = (hhmm ?? "").split(":").map(Number);
  return Number.isFinite(h) && Number.isFinite(m) ? h * 3600 + m * 60 : undefined;
};

/** The demo clock: 04:38:00 when the panel opens, then real seconds. */
function useDemoClock(resetKey: number): number {
  const [start, setStart] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { setStart(Date.now()); setNow(Date.now()); }, [resetKey]);
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);
  return DEMO_START_S + Math.floor((now - start) / 1000);
}

export function TruckBoard({ canCall, onCall, activeOrderId }: { canCall: boolean; onCall: (call: TruckCall) => void; activeOrderId?: string }) {
  const { data, isError, refetch } = useQuery({ queryKey: ["outbound", "truck-calls"], queryFn: fetchBoard, refetchInterval: 4000 });
  const [clockKey, setClockKey] = useState(0);
  const clock = useDemoClock(clockKey);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 space-y-3 border-b border-border px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <span className={cn(SECTION_LABEL, "flex items-center gap-1.5")}>
            <Truck size={12} strokeWidth={1.75} /> Avant le camion
          </span>
          <button
            type="button"
            onClick={() => setClockKey((k) => k + 1)}
            className="flex items-center gap-1 font-mono text-[15px] font-semibold tabular-nums text-foreground hover:text-violet"
            title="Horloge de démonstration : l'ERP est figé à 05:00, après tous les départs. Elle part de 04:38 à l'ouverture. Cliquer pour la remettre à 04:38."
          >
            <Clock size={13} strokeWidth={1.75} className="text-muted-foreground" />
            {hhmmss(clock)}
            <RotateCcw size={11} strokeWidth={1.75} className="text-muted-foreground" />
          </button>
        </div>
        {data ? (
          <div className="grid grid-cols-3 gap-2">
            <Counter label="À appeler" value={<span className="num">{data.toCall}</span>} tone={data.toCall ? "warning" : undefined} />
            <Counter label="En jeu" value={<Money value={data.atStake} compact />} tone="destructive" />
            <Counter label="Récupéré" value={<Money value={data.recovered} compact />} tone={data.recovered ? "success" : undefined} />
          </div>
        ) : null}
        {data ? (
          <p className="text-[11px] text-muted-foreground">
            {data.checked.orders} commandes pesées, {data.checked.lines} lignes relues par le code, sans modèle.
          </p>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto px-3 py-3">
        {isError && !data ? (
          <ErrorState message="Le service IA ne répond pas (GET /ai/outbound/truck-calls)." onRetry={() => refetch()} />
        ) : !data ? (
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-[150px] w-full rounded-[6px]" />)
        ) : (
          <>
            {data.calls.length === 0 ? (
              <p className="px-1 py-6 text-center text-[12px] text-muted-foreground">Rien ne manque dans les camions ce matin.</p>
            ) : null}
            {data.calls.map((c) => (
              <CallCard key={c.orderId} call={c} clock={clock} active={c.orderId === activeOrderId} canCall={canCall} onCall={() => onCall(c)} />
            ))}
            {data.tolerated.length ? (
              <div className="space-y-1.5 pt-2">
                <span className={SECTION_LABEL}>Laissés tranquilles</span>
                {data.tolerated.map((t) => (
                  <div key={`${t.orderId}-${t.productName}`} className="rounded-[6px] border border-dashed border-border px-3 py-2 text-[11.5px] text-muted-foreground">
                    <div className="font-medium">{t.clientName}</div>
                    <div>
                      {t.productName} · {fr(t.ordered)} commandé → {fr(t.onTruck)} {t.unit ?? ""} pesé
                    </div>
                    <div className="italic">{t.why}</div>
                  </div>
                ))}
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

function Counter({ label, value, tone }: { label: string; value: React.ReactNode; tone?: "warning" | "destructive" | "success" }) {
  return (
    <div className="rounded-[6px] border border-border px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-[.06em] text-muted-foreground">{label}</div>
      <div
        className={cn(
          "text-[15px] font-semibold",
          tone === "warning" && "text-warning",
          tone === "destructive" && "text-destructive",
          tone === "success" && "text-success",
        )}
      >
        {value}
      </div>
    </div>
  );
}

function Departure({ departure, clock }: { departure?: string; clock: number }) {
  const dep = toSeconds(departure);
  if (dep === undefined) return null;
  const left = dep - clock;
  if (left <= 0) return <Badge tone="muted">parti à {departure}</Badge>;
  const m = Math.floor(left / 60);
  const s = left % 60;
  return (
    <Badge tone={left <= 5 * 60 ? "destructive" : left <= 15 * 60 ? "warning" : "muted"}>
      part dans {m} min {String(s).padStart(2, "0")}
    </Badge>
  );
}

function CallCard({ call, clock, active, canCall, onCall }: { call: TruckCall; clock: number; active: boolean; canCall: boolean; onCall: () => void }) {
  const done = call.status === "done";
  const rule = RULE[call.substitution];
  return (
    <div
      className={cn(
        "space-y-2 rounded-[6px] border bg-background px-3 py-2.5 text-[12px] transition-colors",
        active ? "border-violet ring-1 ring-violet/40" : "border-border",
        done && "opacity-80",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-[13px] font-semibold">{call.clientName}</div>
          <div className="truncate text-muted-foreground">
            {[call.contact?.name, call.contact?.role, call.city].filter(Boolean).join(" · ")}
          </div>
        </div>
        {done ? (
          <Badge tone="success"><CheckCircle2 size={11} strokeWidth={2} className="mr-0.5 inline" />fait</Badge>
        ) : (
          <Departure departure={call.truck?.departure} clock={clock} />
        )}
      </div>

      <div className="space-y-1">
        {call.problems.map((p, i) => (
          <div key={i} className="flex items-baseline justify-between gap-2">
            <span className="min-w-0">
              <span className="font-medium">{p.productName}</span>{" "}
              <span className={cn(p.kind === "replaced" ? "text-warning" : "text-destructive")}>{KIND_LABEL[p.kind]}</span>
              <span className="text-muted-foreground">
                {" "}· {fr(p.ordered)} → {fr(p.onTruck)} {p.unit ?? ""}
              </span>
              {p.replacedBy ? (
                <span className="block text-muted-foreground">⇄ {fr(p.replacedBy.qty)} {p.replacedBy.unit ?? ""} {p.replacedBy.productName}</span>
              ) : null}
            </span>
            <Money value={p.amount} tone={p.amount < 0 ? "destructive" : undefined} className="shrink-0" />
          </div>
        ))}
      </div>

      {call.truck ? (
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Truck size={12} strokeWidth={1.75} className="shrink-0" />
          <span className="truncate">
            {call.truck.route} · départ {call.truck.departure}
            {call.truck.driver ? ` · ${call.truck.driver}` : ""}
            {call.truck.stop ? ` · arrêt ${call.truck.stop}/${call.truck.stops}` : ""}
          </span>
        </div>
      ) : null}

      <div className="space-y-0.5">
        <Badge tone={rule.tone}>{rule.label}</Badge>
        {call.substitutionRule ? <div className="italic text-muted-foreground">« {call.substitutionRule} »</div> : null}
      </div>

      {done ? (
        <div className="rounded-[4px] bg-success/[.08] px-2 py-1.5">
          <div className="font-medium">{call.outcome?.title ?? "Appel fait"}</div>
          {call.recovered ? <div className="text-success">Récupéré : <Money value={call.recovered} /></div> : null}
        </div>
      ) : (
        <>
          {call.lastAttempt ? (
            <div className="rounded-[4px] bg-warning/[.08] px-2 py-1.5 text-warning">
              <Phone size={11} strokeWidth={2} className="mr-1 inline" />
              Déjà tenté : {call.lastAttempt.replace(/^Appel avant camion\s*:\s*/i, "")}
            </div>
          ) : null}
          <Button size="sm" variant={active ? "default" : "primary"} icon={PhoneOutgoing} onClick={onCall} disabled={!canCall} className="w-full justify-center">
            {active ? "En ligne…" : call.lastAttempt ? "Rappeler" : "Appeler"}
          </Button>
        </>
      )}
    </div>
  );
}

export type { TruckCall };
