#include <iostream>
#include <functional>
#include <chrono>

#define ENABLE_DEBUG true

// Timer decorator
template<typename Func, typename... Args>
auto timer(Func&& func, Args&&... args) {
    auto start = std::chrono::high_resolution_clock::now();
    auto result = std::invoke(std::forward<Func>(func), std::forward<Args>(args)...);
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;
    std::cout << "Function execution took " << elapsed.count() << " seconds\n";
    return result;
}

// Logger decorator
template<typename Func, typename... Args>
auto log_function_call(Func&& func, bool enable_timer = true, Args&&... args) {
    if (ENABLE_DEBUG) {
        std::cout << "Calling function...\n";
        if (enable_timer) {
            return timer(std::forward<Func>(func), std::forward<Args>(args)...);
        } else {
            return std::invoke(std::forward<Func>(func), std::forward<Args>(args)...);
        }
    } else {
        return std::invoke(std::forward<Func>(func), std::forward<Args>(args)...);
    }
}

// Example function
int example_function(int a, int b) {
    return a + b;
}

int main() {
    auto result = log_function_call(example_function, true, 2, 3);
    std::cout << "Result: " << result << '\n';
    return 0;
}