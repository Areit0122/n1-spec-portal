import Head from '@docusaurus/Head';
import useBaseUrl from '@docusaurus/useBaseUrl';

export default function Home() {
  return (
    <>
      <Head><title>3GPP N1 Spec Portal</title></Head>
      <iframe
        title="3GPP N1 Spec Portal"
        src={useBaseUrl('/3gpp_n1_spec_portal_diff_fixed.html?v=6')}
        style={{position: 'fixed', inset: 0, width: '100%', height: '100%', border: 0}}
      />
    </>
  );
}
