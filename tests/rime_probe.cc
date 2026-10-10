// Run only against temporary fixture directories, never a live Rime profile.
#include <rime_api.h>
#include <dlfcn.h>
#include <atomic>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>

static std::atomic<bool> deploy_failed{false};

static void notification(void*, RimeSessionId, const char* type, const char* value) {
  if (std::strcmp(type, "deploy") == 0 && std::strcmp(value, "failure") == 0)
    deploy_failed = true;
}

static void json_string(const char* value) {
  std::cout << '"';
  if (value) {
    for (const unsigned char c : std::string(value)) {
      if (c == '"' || c == '\\') std::cout << '\\' << c;
      else if (c < 32) {
        char escape[7];
        std::snprintf(escape, sizeof(escape), "\\u%04x", c);
        std::cout << escape;
      } else std::cout << c;
    }
  }
  std::cout << '"';
}

int main(int argc, char** argv) {
  if (argc < 7) {
    std::cerr << "usage: rime_probe LIBRIME LUA_PLUGIN SHARED FIXTURE_USER SCHEMA INPUT...\n";
    return 2;
  }
  void* library = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
  if (!library || !dlopen(argv[2], RTLD_NOW | RTLD_GLOBAL)) {
    std::cerr << dlerror() << '\n';
    return 2;
  }
  auto get_api = reinterpret_cast<RimeApi*(*)()>(dlsym(library, "rime_get_api"));
  if (!get_api) return 2;
  RimeApi* api = get_api();
  const char* modules[] = {"default", "lua", nullptr};
  RimeTraits traits{};
  RIME_STRUCT_INIT(RimeTraits, traits);
  traits.shared_data_dir = argv[3];
  traits.user_data_dir = argv[4];
  traits.app_name = "rime.fuyaorime-test";
  traits.modules = modules;
  traits.min_log_level = 2;
  traits.log_dir = argv[4];
  api->setup(&traits);
  api->set_notification_handler(notification, nullptr);
  api->initialize(&traits);
  if (api->start_maintenance(true)) api->join_maintenance_thread();
  if (deploy_failed) { api->finalize(); return 3; }
  auto session = api->create_session();
  if (!session || !api->select_schema(session, argv[5])) {
    api->finalize();
    return 4;
  }
  api->set_option(session, "ascii_mode", false);
  api->set_option(session, "emoji", false);
  for (int i = 6; i < argc; ++i) {
    std::string input = argv[i];
    if (input.rfind("select:", 0) == 0) {
      auto index = std::stoul(input.substr(7));
      if (!api->select_candidate(session, index)) return 5;
      RimeCommit commit{};
      RIME_STRUCT_INIT(RimeCommit, commit);
      if (!api->get_commit(session, &commit)) return 6;
      std::cout << "{\"commit\":";
      json_string(commit.text);
      std::cout << "}\n";
      api->free_commit(&commit);
      continue;
    }
    api->clear_composition(session);
    api->simulate_key_sequence(session, input.c_str());
    RimeContext context{};
    RIME_STRUCT_INIT(RimeContext, context);
    if (!api->get_context(session, &context)) return 7;
    std::cout << "{\"input\":";
    json_string(input.c_str());
    std::cout << ",\"candidates\":[";
    for (int j = 0; j < context.menu.num_candidates; ++j) {
      if (j) std::cout << ',';
      std::cout << "{\"text\":";
      json_string(context.menu.candidates[j].text);
      std::cout << ",\"comment\":";
      json_string(context.menu.candidates[j].comment);
      std::cout << '}';
    }
    std::cout << "]}\n";
    // ASVS 1.4.3: release API-owned context memory after copying its contents.
    api->free_context(&context);
  }
  api->destroy_session(session);
  api->finalize();
  return 0;
}
