import com.sun.tools.attach.VirtualMachine;

public final class R24ReviewAttach
{
    public static void main(String[] args) throws Exception
    {
        int matched = 0;
        for (var descriptor : VirtualMachine.list())
        {
            if (!descriptor.displayName().contains("BootstrapLauncher")) continue;
            var vm = VirtualMachine.attach(descriptor.id());
            try
            {
                if (!"r24-staff".equals(vm.getSystemProperties().getProperty("projectseele.regionalBuild"))) continue;
                vm.loadAgent(args[0], args[1]); matched++;
            }
            finally { vm.detach(); }
        }
        if (matched != 1) throw new IllegalStateException("Expected exactly one isolated R24 test JVM; matched " + matched);
    }
}
