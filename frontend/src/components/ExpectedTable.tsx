import { Fragment, useState } from "react";
import { ExpectedSubnet } from "../types";

const COLUMN_COUNT = 10;

export function ExpectedTable({ subnets }: { subnets: ExpectedSubnet[] }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const toggle = (name: string) =>
    setOpen((prev) => ({ ...prev, [name]: !prev[name] }));

  return (
    <div className="table-scroll">
      <table className="table">
        <thead>
          <tr>
            <th>Subnet</th>
            <th className="mono">Network</th>
            <th className="mono">Broadcast</th>
            <th className="mono">Mask</th>
            <th className="mono">Prefix</th>
            <th>Max hosts</th>
            <th className="mono">First host</th>
            <th className="mono">Last host</th>
            <th className="mono">Gateway</th>
            <th className="c-total">Devices</th>
          </tr>
        </thead>
        <tbody>
          {subnets.map((s) => {
            const isOpen = !!open[s.name];
            const devices = s.devices ?? [];
            const total = devices.reduce((sum, d) => sum + d.count, 0);
            return (
              <Fragment key={s.name}>
                <tr
                  className={`subnet-row${isOpen ? " open" : ""}`}
                  onClick={() => toggle(s.name)}
                >
                  <td className="mono">
                    <button
                      type="button"
                      className="row-toggle"
                      aria-expanded={isOpen}
                      aria-controls={`devs-${s.name}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        toggle(s.name);
                      }}
                    >
                      <span className={`row-caret${isOpen ? " open" : ""}`} aria-hidden="true" />
                      {s.name}
                    </button>
                  </td>
                  <td className="mono">{s.network_address}</td>
                  <td className="mono">{s.broadcast_address}</td>
                  <td className="mono">{s.subnet_mask}</td>
                  <td className="mono">/{s.prefix}</td>
                  <td>{s.max_hosts}</td>
                  <td className="mono">{s.host_first}</td>
                  <td className="mono">{s.host_last}</td>
                  <td className="mono">{s.gateway}</td>
                  <td className="c-total">{total}</td>
                </tr>
                <tr
                  id={`devs-${s.name}`}
                  className={`subnet-devs${isOpen ? " open" : ""}`}
                >
                  <td colSpan={COLUMN_COUNT}>
                    <div className={`disclosure${isOpen ? " open" : ""}`} aria-hidden={!isOpen}>
                      <div>
                        <div className="devs-panel">
                          <div className="devs-title">
                            Expected devices in {s.name}
                          </div>
                          <div className="devs-list">
                            {devices.map((d) => (
                              <div className="dev-item" key={`${d.type}|${d.name}`}>
                                <span className="mono">{d.name}</span>
                                <span className="dev-count">×{d.count}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
