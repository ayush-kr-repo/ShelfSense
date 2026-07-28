import { Canvas } from "@react-three/fiber";
import { OrbitControls, Grid } from "@react-three/drei";

function Shelf({ s, growth }) {
  return (
    <mesh position={[s.x + s.w / 2, 1.1, s.z + s.d / 2]}>   {/* corner→centre, Y-up */}
      <boxGeometry args={[s.w, 2.2, s.d]} />
      <meshStandardMaterial color={growth ? "#f59e0b" : "#57cc99"} />  {/* amber = room to grow */}
    </mesh>
  );
}

export default function Twin({ layout, floorW = 10, floorD = 8, existingCount = 0 }) {
  return (
    <div className="h-[500px] bg-slate-950 rounded-2xl overflow-hidden">
      <Canvas camera={{ position: [12, 10, 16], fov: 60 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 20, 10]} intensity={1.2} />
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[floorW / 2, 0, floorD / 2]}>
          <planeGeometry args={[floorW, floorD]} />
          <meshStandardMaterial color="#1e293b" />
        </mesh>
        <Grid args={[20, 20]} position={[floorW / 2, 0.01, floorD / 2]}
              cellColor="#334155" sectionColor="#475569" />
        {layout.map((s, i) => <Shelf key={s.id} s={s} growth={i >= existingCount} />)}
        <OrbitControls target={[floorW / 2, 0, floorD / 2]} />
      </Canvas>
    </div>
  );
}
