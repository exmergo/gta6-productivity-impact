/* Static HTML counterparts of dex-website's CompassFrame.tsx and CompassArcs.tsx.
 * Source checked 2026-11-12. Same 32px corner boxes, 9px swings, 12px rounded
 * pivots, and 520x380 construction with centre (470,50), radii 110/200/290.
 * Opt in with data-compass-frame="swing|round" or data-compass-work.
 * Decorations never enter slide text and do not take part in layout.
 */
(() => {
  const ns = 'http://www.w3.org/2000/svg';
  const f = n => Math.round(n * 10) / 10;
  const svg = (markup, viewBox, className) => {
    const el = document.createElementNS(ns, 'svg');
    el.setAttribute('viewBox', viewBox);
    el.setAttribute('fill', 'none');
    el.setAttribute('stroke', 'var(--dex-line)');
    el.setAttribute('stroke-width', '1');
    el.setAttribute('aria-hidden', 'true');
    el.setAttribute('class', className);
    el.innerHTML = markup;
    return el;
  };
  document.querySelectorAll('[data-compass-frame]').forEach(box => {
    const layer = document.createElement('span');
    layer.className = 'dex-compass-frame';
    layer.dataset.decoration = '';
    layer.setAttribute('aria-hidden', 'true');
    const round = box.dataset.compassFrame === 'round';
    const p = 27, e = p - 12 * Math.SQRT1_2;
    const mark = round
      ? `<path d="M${p} ${p}L${f(e)} ${f(e)}" stroke-opacity=".7" stroke-dasharray="2 1.5"/><path d="M24 27H30M27 24V30"/>`
      : '<path d="M7 16A9 9 0 0 1 16 7"/>';
    ['tl', 'tr', 'br', 'bl'].forEach(corner => {
      layer.append(svg(mark, '0 0 32 32', 'dex-compass-corner dex-compass-corner--' + corner));
    });
    box.append(layer);
  });
  document.querySelectorAll('[data-compass-work]').forEach(box => {
    const rad = deg => deg * Math.PI / 180;
    const polar = ([x,y],r,deg) => [x+r*Math.cos(rad(deg)), y+r*Math.sin(rad(deg))];
    const arc = (c,r,a0,a1) => {
      const [x0,y0] = polar(c,r,a0), [x1,y1] = polar(c,r,a1);
      return `M${f(x0)} ${f(y0)}A${f(r)} ${f(r)} 0 ${Math.abs(a1-a0)>180?1:0} ${a1>a0?1:0} ${f(x1)} ${f(y1)}`;
    };
    const C = [470,50], radii = [110,200,290];
    const A = polar(C,290,132), B = polar(C,290,168);
    const ab = Math.hypot(B[0]-A[0],B[1]-A[1]), rho = ab*.85;
    const mid = [(A[0]+B[0])/2,(A[1]+B[1])/2];
    const h = Math.sqrt(rho*rho-(ab/2)**2);
    const n = [-(B[1]-A[1])/ab,(B[0]-A[0])/ab];
    const away = n[0]*(mid[0]-C[0])+n[1]*(mid[1]-C[1])>0?1:-1;
    const X = [mid[0]+away*h*n[0],mid[1]+away*h*n[1]];
    const dim = polar(C,200,118);
    const angle = p => Math.atan2(X[1]-p[1],X[0]-p[0])*180/Math.PI;
    const markup = `<g stroke-opacity=".4">${radii.map(r=>`<path d="${arc(C,r,90,185)}"/>`).join('')}</g>
      <g stroke-opacity=".55">${[A,B].map(p=>`<path d="${arc(p,rho,angle(p)-9,angle(p)+9)}"/>`).join('')}</g>
      <path d="M470 50L${f(X[0]+(X[0]-470)*.12)} ${f(X[1]+(X[1]-50)*.12)}" stroke-opacity=".3" stroke-dasharray="6 5"/>
      <g fill="var(--dex-line)" stroke="none"><circle cx="${f(X[0])}" cy="${f(X[1])}" r="2.5" fill-opacity=".6"/>${[A,B].map(p=>`<circle cx="${f(p[0])}" cy="${f(p[1])}" r="2" fill-opacity=".45"/>`).join('')}</g>
      <path d="M470 50L${f(dim[0])} ${f(dim[1])}" stroke-opacity=".5" stroke-dasharray="3 4"/>
      <g stroke-opacity=".6"><path d="M461 50H479M470 41V59"/><circle cx="470" cy="50" r="3"/></g>`;
    box.dataset.decoration = '';
    box.setAttribute('aria-hidden', 'true');
    box.append(svg(markup,'0 0 520 380','dex-compass-work'));
  });
})();
