"use client";

import Image from "next/image";
import { ArrowUpRight, AudioLines, Layers, Radio, ShieldCheck, Sparkles } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { money } from "@/lib/api";
import { specialistArtwork } from "@/lib/specialists";
import type { Agent, RunEvent } from "@/lib/types";

const prettyCapability = (value: string) => value.replaceAll("-", " ");

type AuctionEntryProps = {
  event: RunEvent;
  agents: Agent[];
  onSelect: (agent: Agent) => void;
};

function AuctionEntry({ event, agents, onSelect }: AuctionEntryProps) {
  const rawAgentId = event.data.agent_id;
  const agentId = typeof rawAgentId === "number" || typeof rawAgentId === "string" ? Number(rawAgentId) : null;
  const agent = agentId !== null && Number.isFinite(agentId) ? agents.find((entry) => entry.id === agentId) : undefined;
  const label = event.type === "bid"
    ? "Bid received"
    : event.type === "failover"
      ? "Failover recorded"
      : event.data.failover === true
        ? "Routed next"
        : "Selected for task";
  const price = event.data.price;
  const hasPrice = (typeof price === "number" || typeof price === "string") && Number.isFinite(Number(price));
  const taskId = typeof event.data.task_id === "string" ? event.data.task_id : null;

  return (
    <div className="auction-entry">
      <span className={`auction-entry-icon ${event.type === "win" ? "is-selected" : event.type === "failover" ? "is-failover" : ""}`} aria-hidden="true">
        {event.type === "win" ? <ShieldCheck size={13} /> : event.type === "failover" ? <AudioLines size={13} /> : <Radio size={13} />}
      </span>
      <div className="auction-entry-copy">
        <div className="auction-entry-heading">
          <strong>{agent ? prettyCapability(agent.capability) : agentId !== null ? `Agent #${agentId}` : "Auction event"}</strong>
          <span className="auction-entry-status">{label}</span>
        </div>
        <p>{taskId ? `Task ${taskId}` : "Selection record"}{hasPrice ? ` · ${money(Number(price))} USDC` : ""}</p>
      </div>
      {agent && (
        <button type="button" className="auction-entry-open" onClick={() => onSelect(agent)} aria-label={`Open agent ${agent.id} dossier`}>
          <ArrowUpRight size={14} />
        </button>
      )}
    </div>
  );
}

export function AssemblyDesk({
  agents,
  events,
  loading,
  registryError,
  onSelect,
}: {
  agents: Agent[];
  events: RunEvent[];
  loading: boolean;
  registryError: boolean;
  onSelect: (agent: Agent) => void;
}) {
  const reduceMotion = useReducedMotion();
  const orderedAgents = [...agents].sort((a, b) => Number(b.active) - Number(a.active) || a.capability.localeCompare(b.capability) || a.id - b.id);
  const activeCount = agents.filter((agent) => agent.active).length;
  const auctionEvents = events.filter((event) => ["bid", "win", "failover"].includes(event.type));
  const recentAuctionEvents = auctionEvents.slice(-5).reverse();

  return (
    <section className="assembly-desk" aria-label="Specialist assembly and auction selection">
      <header className="assembly-intro">
        <div>
          <p className="assembly-eyebrow"><span className="assembly-signal" aria-hidden="true" />THE ASSEMBLY DESK <span>/</span> LIVE REGISTRY</p>
          <h2 className="assembly-title">Many kinds of mind.<br /><em>One well-made whole.</em></h2>
        </div>
        <div className="assembly-intro-aside">
          <p>Start with a clear brief. The orchestrator considers real specialist bids, earned reputation and fit, then records how the work is assigned.</p>
          <div className="assembly-tally" aria-label={`${loading || registryError ? "Registry count unavailable" : `${activeCount} active of ${agents.length} registered specialists`}`}>
            <strong>{loading || registryError ? "—" : String(activeCount).padStart(2, "0")}</strong>
            <span>ACTIVE SPECIALISTS<br /><small>{loading || registryError ? "registry status unavailable" : `of ${agents.length} on-chain records`}</small></span>
          </div>
        </div>
      </header>

      <div className="assembly-workbench">
        <section className="assembly-registry" aria-labelledby="assembly-registry-title" aria-busy={loading}>
          <div className="registry-heading">
            <div>
              <p className="assembly-overline">THE FIELD GUIDE</p>
              <h3 id="assembly-registry-title">Meet the specialists</h3>
              <p className="registry-subtitle">A closer look at the minds registered for the work.</p>
            </div>
            <figure className="registry-illustration" aria-hidden="true">
              <Image src="/images/assembly-bookplate.webp" alt="" width={540} height={360} sizes="(max-width: 760px) 36vw, 220px" />
            </figure>
          </div>

          {loading ? (
            <div className="registry-state" role="status"><span className="assembly-loader" aria-hidden="true" /><p>Fetching current registry records…</p></div>
          ) : registryError ? (
            <div className="registry-state registry-state-error" role="status"><Layers size={19} /><p>The registry could not be reached. Specialist records have not been assumed.</p></div>
          ) : orderedAgents.length ? (
            <div className="specialist-grid">
              {orderedAgents.map((agent, index) => {
                const artwork = specialistArtwork[agent.capability];
                return (
                  <motion.button
                    key={agent.id}
                    type="button"
                    className={`specialist-card ${agent.active ? "is-active" : "is-inactive"}`}
                    onClick={() => onSelect(agent)}
                    aria-label={`Open ${prettyCapability(agent.capability)} agent ${agent.id} dossier`}
                    initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35, delay: reduceMotion ? 0 : Math.min(index * 0.035, 0.21) }}
                    whileHover={reduceMotion ? undefined : { y: -2 }}
                    whileTap={reduceMotion ? undefined : { scale: 0.99 }}
                  >
                    <span className={`specialist-symbol ${artwork ? "has-artwork" : ""}`} aria-hidden="true">
                      {artwork ? (
                        <Image src={artwork} alt="" width={48} height={48} sizes="48px" />
                      ) : (
                        <Sparkles size={17} strokeWidth={1.6} />
                      )}
                    </span>
                    <span className="specialist-copy">
                      <span className="specialist-name">{prettyCapability(agent.capability)}</span>
                      <span className="specialist-id">AGENT #{agent.id} <i /> {agent.active ? "AVAILABLE" : "INACTIVE"}</span>
                    </span>
                    <span className="specialist-price">{money(agent.price)}<small>USDC / CALL</small></span>
                    <ArrowUpRight className="specialist-open" size={13} aria-hidden="true" />
                    <span className="specialist-reputation">REPUTATION <strong>{(agent.reputation / 100).toFixed(1)}</strong><span>/ 100</span></span>
                  </motion.button>
                );
              })}
            </div>
          ) : (
            <div className="registry-state" role="status"><Layers size={19} /><p>No registered specialists were returned. This roster will fill from confirmed registry records.</p></div>
          )}

          <p className="registry-note"><span aria-hidden="true">↗</span> Open a dossier for verified registry details. Assignment stays with the orchestrator.</p>
        </section>

        <aside className="auction-panel" aria-labelledby="auction-panel-title">
          <div className="auction-panel-top">
            <div><p className="assembly-overline">SELECTION &amp; FIT</p><span className="auction-status"><i aria-hidden="true" />RECORDED, NOT GUESSED</span></div>
            <figure className="auction-illustration" aria-hidden="true">
              <Image src="/images/auction-engraving.webp" alt="" width={300} height={200} sizes="150px" />
            </figure>
          </div>
          <h3 id="auction-panel-title">Let the right bid surface.</h3>
          <p className="auction-intro-copy">Each task opens its own considered auction. Follow the recorded bids and the orchestrator’s choice as a real mission unfolds.</p>

          <div className="auction-ledger">
            <div className="auction-ledger-heading"><span>SELECTION LEDGER</span><span className="auction-ledger-count">{auctionEvents.length ? `${auctionEvents.length} RECORDED` : "AWAITING A BRIEF"}</span></div>
            {recentAuctionEvents.length ? (
              <div className="auction-event-list" aria-live="polite">
                {recentAuctionEvents.map((event) => <AuctionEntry key={event.id} event={event} agents={agents} onSelect={onSelect} />)}
              </div>
            ) : (
              <div className="auction-empty">
                <span className="auction-empty-mark" aria-hidden="true"><AudioLines size={17} /></span>
                <p>Your first brief opens the floor.</p>
                <span>Once work begins, actual bids, assignments and handoffs appear here — never sample entries.</span>
              </div>
            )}
          </div>
          <p className="auction-note"><Sparkles size={12} aria-hidden="true" /> The panel follows durable mission events; it never overrides automated assignment.</p>
        </aside>
      </div>
    </section>
  );
}
