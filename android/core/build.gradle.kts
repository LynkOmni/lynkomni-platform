// NOT built in the sandbox (no Kotlin toolchain there). Run `./gradlew :core:test` in CI.
plugins { kotlin("jvm") version "2.0.0" }
repositories { mavenCentral() }
dependencies { testImplementation(kotlin("test")); testImplementation("org.json:json:20260814"); implementation("org.json:json:20260814") }
tasks.test { useJUnitPlatform() }
