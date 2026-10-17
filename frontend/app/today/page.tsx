"use client";

import { useEffect, useState } from "react";
import EditionView from "../../components/EditionView";
import SkeletonEdition from "../../components/SkeletonEdition";
import OfflineBanner from "../../components/OfflineBanner";
import { getEdition, type EditionResult } from "../../lib/api";
import { useReader } from "../../lib/reader";

export default function TodayPage() {
    const [readerId] = useReader();
    const [result, setResult] = useState<EditionResult | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      if (!readerId) return;
      let mounted = true;
      (async () => {
        const res = await getEdition(readerId, "today");
        if (!mounted) return;
        setResult(res);
        setLoading(false);
      })();
      return () => {
        mounted = false;
      };
    }, [readerId]);

    if (loading) return <SkeletonEdition />;
    if (!result || !result.edition) {
      return (
        <div className="page">
          <p>No edition available yet. Onboard first to set the presses.</p>
        </div>
      );
    }

    return (
      <>
       {result.offline && <OfflineBanner />}
       <EditionView edition={result.edition} />
      </>
    );
}
