// src/types.d.ts

// این خط به TypeScript می‌گوید که ماژول‌های three/examples/jsm/loaders/ را به عنوان ماژول‌های معتبر بپذیرد
declare module 'three/examples/jsm/loaders/GLTFLoader' {
    import { Loader, LoadingManager, Object3D, AnimationClip, Group } from 'three';

    export class GLTFLoader extends Loader {
        constructor(manager?: LoadingManager);
        load(
            url: string,
            onLoad: (gltf: GLTF) => void,
            onProgress?: (event: ProgressEvent) => void,
            onError?: (event: ErrorEvent) => void
        ): void;
        parse(data: ArrayBuffer, path: string, onLoad: (gltf: GLTF) => void, onError?: (event: ErrorEvent) => void): void;
    }

    export interface GLTF {
        animations: AnimationClip[];
        scene: Group;
        scenes: Group[];
        cameras: THREE.Camera[];
        asset: object;
        parser: object;
        userData: object;
    }
}

// اگر از ماژول‌های دیگری در jsm استفاده می‌کنید، آن‌ها را نیز اینجا تعریف کنید
// declare module 'three/examples/jsm/controls/OrbitControls' {
//     export * from 'three/src/Three';
// }