// Small native launchers register three savers while sharing one frozen runtime.
#include <windows.h>
#include <string>
#include <vector>

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR arguments, int) {
    std::vector<wchar_t> path(32768);
    if (!GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()))) return 1;
    std::wstring host(path.data());
    host = host.substr(0, host.find_last_of(L"\\/")) + L"\\RetroScreensaver.exe";
    if (GetFileAttributesW(host.c_str()) == INVALID_FILE_ATTRIBUTES) {
        DWORD bytes = static_cast<DWORD>(path.size() * sizeof(wchar_t));
        if (RegGetValueW(HKEY_LOCAL_MACHINE, L"Software\\RetroGamingScreensavers",
                        L"RuntimePath", RRF_RT_REG_SZ, nullptr, path.data(), &bytes) != ERROR_SUCCESS) {
            MessageBoxW(nullptr, L"The screensaver runtime is missing. Reinstall Retro Gaming Screensavers.",
                        L"Retro Gaming Screensavers", MB_OK | MB_ICONERROR);
            return 1;
        }
        host = std::wstring(path.data()) + L"\\RetroScreensaver.exe";
    }
    // Forward Windows /s, /c and /p arguments without a shell or re-quoting.
    std::wstring command = L"\"" + host + L"\" --game " RETRO_GAME L" ";
    command += arguments;
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION child{};
    if (!CreateProcessW(host.c_str(), command.data(), nullptr, nullptr, FALSE,
                        CREATE_SUSPENDED, nullptr, nullptr, &startup, &child)) {
        MessageBoxW(nullptr, L"Could not start the screensaver. Reinstall Retro Gaming Screensavers.",
                    L"Retro Gaming Screensavers", MB_OK | MB_ICONERROR);
        return 1;
    }
    HANDLE job = CreateJobObjectW(nullptr, nullptr);
    if (job) {
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits));
        AssignProcessToJobObject(job, child.hProcess);
    }
    ResumeThread(child.hThread);
    CloseHandle(child.hThread);
    WaitForSingleObject(child.hProcess, INFINITE);
    DWORD result = 1;
    GetExitCodeProcess(child.hProcess, &result);
    CloseHandle(child.hProcess);
    if (job) CloseHandle(job);
    return static_cast<int>(result);
}
