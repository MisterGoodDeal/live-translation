import { Link } from "@heroui/link";

import { Head } from "./head";

import { Navbar } from "@/components/navbar";
import { SocketContext } from "../contexts/socket.contexts";
import React from "react";

export default function DefaultLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const socket = React.useContext(SocketContext);
  return (
    <SocketContext.Provider value={socket}>
      <div className="relative flex flex-col h-screen">
        <main className="container mx-auto max-w-7xl flex-grow">
          {children}
        </main>
      </div>
    </SocketContext.Provider>
  );
}
