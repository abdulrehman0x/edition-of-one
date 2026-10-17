"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import EditionView from "../../../components/EditionView";
import SkeletonEdition from "../../../components/SkeletonEdition";
import OfflineBanner from "../../../components/OfflineBanner";
import { getEdition, type EditionResult } from "../../../lib/api";
import { useReader } from "../../../lib/reader";

export default function EditionByDatePage() {
 const params = useParams<{ date: string }>();
 const [readerId] = useReader();
 const [result, setResult] = useState<EditionResult | null>(null);
 const [loading, setLoading] = useState(true);

 useEffect(() => {
   if (!readerId || !params?.date) return;
   let mounted = true;
   (async () => {
     const res = await getEdition(readerId, params.date);
     if (!mounted) return;
     setResult(res);
     setLoading(false);
   })();
   return () => {
     mounted = false;
   };
 }, [readerId, params?.date]);

 if (loading) return <SkeletonEdition />;
 if (!result || !result.edition) {
   return (
     <div className="page">
       <p>No edition found for {params?.date}.</p>
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
